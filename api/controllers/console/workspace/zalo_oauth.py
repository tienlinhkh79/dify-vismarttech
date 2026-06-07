"""Console endpoints for Zalo OA OAuth + QR connect."""

from __future__ import annotations

from flask import request
from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from werkzeug.exceptions import BadRequest, NotFound

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from models.trigger import OmniChannelType
from services.omnichannel.channel_management_service import ChannelManagementService
from services.omnichannel.zalo_oauth_service import ZaloOAuthService


class ZaloOaProvisionPayload(BaseModel):
    oauth_application_id: str = Field(min_length=1, max_length=255)
    client_secret: str = Field(min_length=1, max_length=255)


class OAuthChannelProvisionPayload(BaseModel):
    channel_type: str = Field(min_length=1, max_length=64)


@console_ns.route("/workspaces/current/channels/oauth/provision")
class OAuthChannelProvisionApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = OAuthChannelProvisionPayload.model_validate(console_ns.payload or request.get_json(silent=True) or {})
        try:
            data = ChannelManagementService.provision_oauth_channel_draft(
                tenant_id,
                account.id,
                channel_type=payload.channel_type,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201


@console_ns.route("/workspaces/current/channels/zalo-oa/provision")
class ZaloOaProvisionApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = ZaloOaProvisionPayload.model_validate(console_ns.payload or {})
        try:
            data = ChannelManagementService.provision_zalo_oa_draft(
                tenant_id,
                account.id,
                oauth_application_id=payload.oauth_application_id,
                client_secret=payload.client_secret,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201


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
