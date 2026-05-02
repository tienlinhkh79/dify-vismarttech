"""Console endpoints for Zalo OA OAuth + QR connect."""

from __future__ import annotations

from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from werkzeug.exceptions import NotFound

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from models.trigger import OmniChannelType
from services.omnichannel.channel_management_service import ChannelManagementService
from services.omnichannel.zalo_oauth_service import ZaloOAuthService


@console_ns.route("/workspaces/current/channels/zalo/<string:channel_id>/oauth/start")
class ZaloChannelOAuthStartApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel or channel["channel_type"] != OmniChannelType.ZALO_OA.value:
            raise NotFound("Channel not found")
        try:
            data = ZaloOAuthService.start(tenant_id, channel_id)
        except ValueError as e:
            return {"error": str(e)}, 400
        return jsonable_encoder({"data": data}), 200


@console_ns.route("/workspaces/current/channels/zalo/<string:channel_id>/oauth/status")
class ZaloChannelOAuthStatusApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel or channel["channel_type"] != OmniChannelType.ZALO_OA.value:
            raise NotFound("Channel not found")
        try:
            data = ZaloOAuthService.connection_status(tenant_id, channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": data}), 200
