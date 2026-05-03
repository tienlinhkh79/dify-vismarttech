from __future__ import annotations

from flask import request
from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator
from werkzeug.exceptions import BadRequest, NotFound

from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from libs.login import current_account_with_tenant, login_required
from models.trigger import OmniChannelCrmLeadStage
from services.omnichannel.mini_crm_service import MiniCrmService


class MiniCrmLeadPatchPayload(BaseModel):
    stage: str | None = Field(default=None, max_length=32)
    owner_account_id: str | None = Field(default=None, max_length=36)
    notes: str | None = Field(default=None, max_length=65535)
    source_override: str | None = Field(default=None, max_length=512)

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            OmniChannelCrmLeadStage(value)
        except ValueError as exc:
            raise ValueError(f"Invalid stage: {value}") from exc
        return value


register_schema_models(console_ns, MiniCrmLeadPatchPayload)


@console_ns.route("/workspaces/current/mini-crm/leads")
class MiniCrmLeadCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        channel_type = request.args.get("channel_type") or None
        stage = request.args.get("stage") or None
        search_query = request.args.get("q") or None
        try:
            page_offset = int(request.args.get("offset") or 0)
        except ValueError:
            page_offset = 0
        try:
            page_size = int(request.args.get("limit") or 50)
        except ValueError:
            page_size = 50
        result = MiniCrmService.list_leads(
            tenant_id=tenant_id,
            channel_type=channel_type,
            stage=stage,
            search_query=search_query,
            page_offset=page_offset,
            page_size=page_size,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/leads/<string:conversation_id>")
class MiniCrmLeadApi(Resource):
    @console_ns.expect(console_ns.models[MiniCrmLeadPatchPayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            payload = MiniCrmLeadPatchPayload.model_validate(console_ns.payload or {})
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        body = payload.model_dump(exclude_unset=True)
        if not body:
            raise BadRequest("At least one field must be provided")
        lead_patch_call_kwargs: dict[str, object] = {"tenant_id": tenant_id, "conversation_id": conversation_id}
        if "stage" in body:
            lead_patch_call_kwargs["stage"] = body["stage"]
        if "owner_account_id" in body:
            lead_patch_call_kwargs["owner_account_id"] = body["owner_account_id"]
        if "notes" in body:
            lead_patch_call_kwargs["notes"] = body["notes"]
        if "source_override" in body:
            lead_patch_call_kwargs["source_override"] = body["source_override"]
        try:
            updated = MiniCrmService.patch_lead(**lead_patch_call_kwargs)
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        if not updated:
            raise NotFound("Conversation not found")
        return jsonable_encoder({"data": updated})
