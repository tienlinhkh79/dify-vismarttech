from __future__ import annotations

from datetime import datetime

from flask import request
from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator, model_validator
from werkzeug.exceptions import NotFound

from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from services.omnichannel.channel_management_service import ChannelInput, ChannelManagementService
from services.omnichannel.kiotviet_connection_service import KiotVietConnectionInput, KiotVietConnectionService
from services.omnichannel.omnichannel_ops_service import OmnichannelOpsService
from services.omnichannel.providers.registry import ChannelProviderRegistry
from tasks.omnichannel_tasks import run_omnichannel_sync_job


class MessengerChannelCreatePayload(BaseModel):
    channel_id: str = Field(min_length=1, max_length=255)
    app_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    page_id: str = Field(min_length=1, max_length=255)
    verify_token: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)
    page_access_token: str = Field(min_length=1)
    graph_api_version: str = Field(default="v23.0", min_length=1, max_length=32)
    enabled: bool = True


class MessengerChannelUpdatePayload(BaseModel):
    app_id: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    page_id: str | None = Field(default=None, min_length=1, max_length=255)
    verify_token: str | None = Field(default=None, min_length=1)
    app_secret: str | None = Field(default=None, min_length=1)
    page_access_token: str | None = Field(default=None, min_length=1)
    graph_api_version: str | None = Field(default=None, min_length=1, max_length=32)
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_not_empty(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self


class ChannelCreatePayload(BaseModel):
    channel_type: str = Field(min_length=1, max_length=60)
    channel_id: str = Field(min_length=1, max_length=255)
    app_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    external_resource_id: str = Field(min_length=1, max_length=255)
    verify_token: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    access_token: str = Field(default="", max_length=16384)
    oauth_application_id: str | None = Field(default=None, max_length=255)
    api_version: str = Field(default="v23.0", min_length=1, max_length=32)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_access_token_by_channel(self):
        if self.channel_type == "zalo_oa":
            if not self.access_token.strip() and not (self.oauth_application_id or "").strip():
                raise ValueError("Zalo OA requires oauth_application_id when access_token is empty")
            return self
        if not self.access_token.strip():
            raise ValueError("access_token is required for this channel type")
        return self


class ChannelUpdatePayload(BaseModel):
    channel_type: str | None = Field(default=None, min_length=1, max_length=60)
    app_id: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    external_resource_id: str | None = Field(default=None, min_length=1, max_length=255)
    verify_token: str | None = Field(default=None, min_length=1)
    client_secret: str | None = Field(default=None, min_length=1)
    access_token: str | None = Field(default=None, max_length=16384)
    oauth_application_id: str | None = Field(default=None, max_length=255)
    api_version: str | None = Field(default=None, min_length=1, max_length=32)
    enabled: bool | None = None

    @field_validator("access_token", mode="before")
    @classmethod
    def empty_access_token_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_not_empty(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self


class KiotVietConnectionCreatePayload(BaseModel):
    connection_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: str = Field(min_length=1)
    retailer_name: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class KiotVietConnectionUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_id: str | None = Field(default=None, min_length=1, max_length=255)
    client_secret: str | None = Field(default=None, min_length=1)
    retailer_name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_not_empty(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self


class ChannelSyncHistoryPayload(BaseModel):
    since: datetime | None = None
    until: datetime | None = None


class ChannelTimeFilterPayload(BaseModel):
    since: datetime | None = None
    until: datetime | None = None
    cursor: str | None = None
    limit: int | None = Field(default=None, ge=1, le=100)


register_schema_models(
    console_ns,
    MessengerChannelCreatePayload,
    MessengerChannelUpdatePayload,
    ChannelCreatePayload,
    ChannelUpdatePayload,
    KiotVietConnectionCreatePayload,
    KiotVietConnectionUpdatePayload,
    ChannelSyncHistoryPayload,
    ChannelTimeFilterPayload,
)


def _messenger_to_channel_input(payload: MessengerChannelCreatePayload) -> ChannelInput:
    data = payload.model_dump()
    return ChannelInput(
        channel_type="facebook_messenger",
        channel_id=data["channel_id"],
        app_id=data["app_id"],
        name=data["name"],
        external_resource_id=data["page_id"],
        verify_token=data["verify_token"],
        client_secret=data["app_secret"],
        access_token=data["page_access_token"],
        api_version=data["graph_api_version"],
        enabled=data["enabled"],
    )


def _messenger_update_to_generic(payload: MessengerChannelUpdatePayload) -> dict[str, object]:
    generic_payload: dict[str, object] = {}
    mapped_fields = {
        "app_id": "app_id",
        "name": "name",
        "page_id": "external_resource_id",
        "verify_token": "verify_token",
        "app_secret": "client_secret",
        "page_access_token": "access_token",
        "graph_api_version": "api_version",
        "enabled": "enabled",
    }
    for source_field, target_field in mapped_fields.items():
        value = getattr(payload, source_field)
        if value is not None:
            generic_payload[target_field] = value
    return generic_payload


@console_ns.route("/workspaces/current/channels/providers")
class ChannelProviderCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        return jsonable_encoder({"data": ChannelProviderRegistry.list()})


@console_ns.route("/workspaces/current/channels")
class ChannelCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        return jsonable_encoder({"data": ChannelManagementService.list_channels(tenant_id)})

    @console_ns.expect(console_ns.models[ChannelCreatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = ChannelCreatePayload.model_validate(console_ns.payload or {})
        try:
            created = ChannelManagementService.create_channel(
                tenant_id=tenant_id,
                user_id=account.id,
                payload=ChannelInput(**payload.model_dump()),
            )
        except ValueError as e:
            return {"error": str(e)}, 400
        return jsonable_encoder({"data": created}), 201


@console_ns.route("/workspaces/current/channels/<string:channel_id>")
class ChannelApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": channel})

    @console_ns.expect(console_ns.models[ChannelUpdatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def patch(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = ChannelUpdatePayload.model_validate(console_ns.payload or {})
        try:
            updated = ChannelManagementService.update_channel(
                tenant_id=tenant_id,
                channel_id=channel_id,
                payload=payload.model_dump(exclude_none=True),
            )
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": updated})

    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def delete(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            ChannelManagementService.delete_channel(tenant_id, channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return {"result": "success"}, 200


@console_ns.route("/workspaces/current/channels/<string:channel_id>/conversations")
class ChannelConversationCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        filter_payload = ChannelTimeFilterPayload.model_validate(request.args.to_dict())
        result = OmnichannelOpsService.list_conversations(
            tenant_id=tenant_id,
            channel_id=channel_id,
            since=filter_payload.since,
            until=filter_payload.until,
            cursor=filter_payload.cursor,
            limit=filter_payload.limit,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/channels/<string:channel_id>/conversations/<string:conversation_id>/messages")
class ChannelConversationMessageCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        filter_payload = ChannelTimeFilterPayload.model_validate(request.args.to_dict())
        result = OmnichannelOpsService.list_messages(
            tenant_id=tenant_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            since=filter_payload.since,
            until=filter_payload.until,
            cursor=filter_payload.cursor,
            limit=filter_payload.limit,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/channels/<string:channel_id>/sync-history")
class ChannelSyncHistoryApi(Resource):
    @console_ns.expect(console_ns.models[ChannelSyncHistoryPayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self, channel_id: str):
        account, tenant_id = current_account_with_tenant()
        payload = ChannelSyncHistoryPayload.model_validate(console_ns.payload or {})
        try:
            job = OmnichannelOpsService.create_sync_job(
                tenant_id=tenant_id,
                channel_id=channel_id,
                created_by=account.id,
                since=payload.since,
                until=payload.until,
            )
        except ValueError:
            raise NotFound("Channel not found")
        run_omnichannel_sync_job.delay(tenant_id, channel_id, job["id"])
        return jsonable_encoder({"data": job}), 202


@console_ns.route("/workspaces/current/channels/<string:channel_id>/sync-jobs/<string:job_id>")
class ChannelSyncJobApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str, job_id: str):
        _, tenant_id = current_account_with_tenant()
        job = OmnichannelOpsService.get_sync_job(tenant_id=tenant_id, channel_id=channel_id, job_id=job_id)
        if not job:
            raise NotFound("Sync job not found")
        return jsonable_encoder({"data": job})


@console_ns.route("/workspaces/current/channels/<string:channel_id>/stats")
class ChannelStatsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        filter_payload = ChannelTimeFilterPayload.model_validate(request.args.to_dict())
        data = OmnichannelOpsService.get_channel_stats(
            tenant_id=tenant_id,
            channel_id=channel_id,
            since=filter_payload.since,
            until=filter_payload.until,
        )
        return jsonable_encoder({"data": data})


@console_ns.route("/workspaces/current/channels/<string:channel_id>/health")
class ChannelHealthApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            data = OmnichannelOpsService.get_health(tenant_id=tenant_id, channel_id=channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": data})


@console_ns.route("/workspaces/current/channels/<string:channel_id>/webhook/test")
class ChannelWebhookTestApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            data = OmnichannelOpsService.test_webhook(tenant_id=tenant_id, channel_id=channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": data})


@console_ns.route("/workspaces/current/omnichannel/messenger/channels")
class MessengerChannelCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        return jsonable_encoder({"data": ChannelManagementService.list_messenger_channels(tenant_id)})

    @console_ns.expect(console_ns.models[MessengerChannelCreatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = MessengerChannelCreatePayload.model_validate(console_ns.payload or {})
        try:
            created = ChannelManagementService.create_messenger_channel(
                tenant_id=tenant_id,
                user_id=account.id,
                payload=_messenger_to_channel_input(payload),
            )
        except ValueError as e:
            return {"error": str(e)}, 400
        return jsonable_encoder({"data": created}), 201


@console_ns.route("/workspaces/current/channels/messenger")
class MessengerChannelCollectionV2Api(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        return jsonable_encoder({"data": ChannelManagementService.list_messenger_channels(tenant_id)})

    @console_ns.expect(console_ns.models[MessengerChannelCreatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = MessengerChannelCreatePayload.model_validate(console_ns.payload or {})
        try:
            created = ChannelManagementService.create_messenger_channel(
                tenant_id=tenant_id,
                user_id=account.id,
                payload=_messenger_to_channel_input(payload),
            )
        except ValueError as e:
            return {"error": str(e)}, 400
        return jsonable_encoder({"data": created}), 201


@console_ns.route("/workspaces/current/omnichannel/messenger/channels/<string:channel_id>")
class MessengerChannelApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_messenger_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": channel})

    @console_ns.expect(console_ns.models[MessengerChannelUpdatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def patch(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = MessengerChannelUpdatePayload.model_validate(console_ns.payload or {})
        try:
            updated = ChannelManagementService.update_messenger_channel(
                tenant_id=tenant_id,
                channel_id=channel_id,
                payload=_messenger_update_to_generic(payload),
            )
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": updated})

    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def delete(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            ChannelManagementService.delete_messenger_channel(tenant_id, channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return {"result": "success"}, 200


@console_ns.route("/workspaces/current/channels/messenger/<string:channel_id>")
class MessengerChannelV2Api(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_messenger_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": channel})

    @console_ns.expect(console_ns.models[MessengerChannelUpdatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def patch(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = MessengerChannelUpdatePayload.model_validate(console_ns.payload or {})
        try:
            updated = ChannelManagementService.update_messenger_channel(
                tenant_id=tenant_id,
                channel_id=channel_id,
                payload=_messenger_update_to_generic(payload),
            )
        except ValueError:
            raise NotFound("Channel not found")
        return jsonable_encoder({"data": updated})

    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def delete(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            ChannelManagementService.delete_messenger_channel(tenant_id, channel_id)
        except ValueError:
            raise NotFound("Channel not found")
        return {"result": "success"}, 200


@console_ns.route("/workspaces/current/channels/kiotviet")
class KiotVietConnectionCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        account, tenant_id = current_account_with_tenant()
        return jsonable_encoder({"data": KiotVietConnectionService.list_connections(tenant_id, account.id)})

    @console_ns.expect(console_ns.models[KiotVietConnectionCreatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = KiotVietConnectionCreatePayload.model_validate(console_ns.payload or {})
        try:
            created = KiotVietConnectionService.create_connection(
                tenant_id=tenant_id,
                user_id=account.id,
                payload=KiotVietConnectionInput(**payload.model_dump()),
            )
        except ValueError as e:
            return {"error": str(e)}, 400
        return jsonable_encoder({"data": created}), 201


@console_ns.route("/workspaces/current/channels/kiotviet/<string:connection_id>")
class KiotVietConnectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, connection_id: str):
        _, tenant_id = current_account_with_tenant()
        connection = KiotVietConnectionService.get_connection(tenant_id, connection_id)
        if not connection:
            raise NotFound("Connection not found")
        return jsonable_encoder({"data": connection})

    @console_ns.expect(console_ns.models[KiotVietConnectionUpdatePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def patch(self, connection_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = KiotVietConnectionUpdatePayload.model_validate(console_ns.payload or {})
        try:
            updated = KiotVietConnectionService.update_connection(
                tenant_id=tenant_id,
                connection_id=connection_id,
                payload=payload.model_dump(exclude_none=True),
            )
        except ValueError:
            raise NotFound("Connection not found")
        return jsonable_encoder({"data": updated})

    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def delete(self, connection_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            KiotVietConnectionService.delete_connection(tenant_id, connection_id)
        except ValueError:
            raise NotFound("Connection not found")
        return {"result": "success"}, 200

