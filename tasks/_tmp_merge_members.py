from pathlib import Path

up = Path(r"C:\chatbot\dify-upstream-1.16.1\api\controllers\console\workspace\members.py").read_text(encoding="utf-8")
dst = Path(r"c:\chatbot\dify\api\controllers\console\workspace\members.py")

if "MiniCrmAccessService" in up:
    dst.write_text(up, encoding="utf-8")
    raise SystemExit("already has MiniCrm")

# imports
up = up.replace(
    "from flask_restx import Resource\n",
    "from flask_restx import Resource\n"
    "from graphon.model_runtime.utils.encoders import jsonable_encoder\n",
)
up = up.replace(
    "from services.feature_service import FeatureService\n",
    "from services.feature_service import FeatureService\n"
    "from services.omnichannel.mini_crm_access_service import MiniCrmAccessService\n",
)

payload = '''
class MemberMiniCrmVerticalsPayload(BaseModel):
    verticals: list[str] = Field(default_factory=list, max_length=10)

'''

# Insert payload after OwnerTransferPayload class block - find first route
marker = "@console_ns.route("
idx = up.find(marker)
if idx < 0:
    raise SystemExit("route marker not found")
up = up[:idx] + payload + up[idx:]

# Register schema if there is a register_schema_models / similar pattern for payloads
# 1.16 may use different registration; API expect() needs model on console_ns.
# Add schema_model registration near other payload classes if MemberInvitePayload exists.
if "MemberInvitePayload" in up and "reg(MemberMiniCrmVerticalsPayload)" not in up:
    # Try console_ns.schema_model pattern used elsewhere in file
    if "console_ns.schema_model" in up:
        insert_at = up.rfind("console_ns.schema_model")
        # append after last schema_model line
        line_end = up.find("\n", insert_at)
        up = (
            up[: line_end + 1]
            + "console_ns.schema_model(\n"
            + '    MemberMiniCrmVerticalsPayload.__name__,\n'
            + "    MemberMiniCrmVerticalsPayload.model_json_schema(),\n"
            + ")\n"
            + up[line_end + 1 :]
        )
    else:
        # fallback: register right before first route
        idx = up.find(marker)
        up = (
            up[:idx]
            + "console_ns.schema_model(\n"
            + "    MemberMiniCrmVerticalsPayload.__name__,\n"
            + "    MemberMiniCrmVerticalsPayload.model_json_schema(),\n"
            + ")\n\n"
            + up[idx:]
        )

api = '''
@console_ns.route("/workspaces/current/members/<uuid:member_id>/mini-crm-verticals")
class MemberMiniCrmVerticalsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, member_id):
        current_user, tenant_id = current_account_with_tenant()
        if not current_user.is_admin_or_owner:
            return {"code": "forbidden", "message": "No permission"}, 403
        member = db.session.get(Account, str(member_id))
        if member is None or not TenantService.is_member(member, current_user.current_tenant):
            abort(404)
        verticals = MiniCrmAccessService.list_verticals_for_member(
            tenant_id=tenant_id,
            account_id=str(member_id),
        )
        return jsonable_encoder({"data": {"verticals": verticals}})

    @console_ns.expect(console_ns.models[MemberMiniCrmVerticalsPayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def put(self, member_id):
        current_user, tenant_id = current_account_with_tenant()
        if not current_user.is_admin_or_owner:
            return {"code": "forbidden", "message": "No permission"}, 403
        member = db.session.get(Account, str(member_id))
        if member is None or not TenantService.is_member(member, current_user.current_tenant):
            abort(404)
        if TenantService.is_owner(member, current_user.current_tenant):
            return {"code": "invalid-target", "message": "Owner has access to all CRM verticals"}, 400
        try:
            payload = MemberMiniCrmVerticalsPayload.model_validate(console_ns.payload or {})
        except ValueError as exc:
            return {"code": "invalid-payload", "message": str(exc)}, 400
        verticals = MiniCrmAccessService.set_member_verticals(
            tenant_id=tenant_id,
            account_id=str(member_id),
            verticals=payload.verticals,
        )
        return jsonable_encoder({"data": {"verticals": verticals}})
'''

up = up.rstrip() + "\n\n" + api.lstrip() + "\n"
dst.write_text(up, encoding="utf-8")
print("wrote", dst, "lines", len(up.splitlines()))
