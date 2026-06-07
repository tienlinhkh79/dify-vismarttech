from __future__ import annotations

from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from werkzeug.exceptions import BadRequest, NotFound

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.channel_management_service import ChannelManagementService
from services.omnichannel.zalo_personal_session_service import ZaloPersonalSessionService


@console_ns.route("/workspaces/current/channels/zalo-personal/provision")
class ZaloPersonalProvisionApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        try:
            data = ChannelManagementService.provision_zalo_personal_draft(tenant_id, account.id)
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201


@console_ns.route("/workspaces/current/channels/zalo-personal/<string:channel_id>/login/start")
class ZaloPersonalLoginStartApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        if channel.get("channel_type") != "zalo_personal":
            raise BadRequest("Channel is not Zalo Personal")
        try:
            data = ZaloPersonalSessionService.start_login(channel_id)
            cfg = ChannelConfigService.get_zalo_personal_channel_config(channel_id, require_enabled=False)
            if cfg:
                ZaloPersonalSessionService.notify_worker_webhook(
                    channel_id,
                    verify_token=cfg["verify_token"],
                )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data})


@console_ns.route("/workspaces/current/channels/zalo-personal/<string:channel_id>/login/status")
class ZaloPersonalLoginStatusApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        if channel.get("channel_type") != "zalo_personal":
            raise BadRequest("Channel is not Zalo Personal")
        status = ZaloPersonalSessionService.get_login_status(channel_id)
        return jsonable_encoder({"data": {"status": status, "connected": status == "connected"}})
