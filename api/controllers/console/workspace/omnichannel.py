from __future__ import annotations

from flask_restx import Resource
from dify_graph.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field, model_validator
from werkzeug.exceptions import NotFound

from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from services.omnichannel.channel_management_service import ChannelInput, ChannelManagementService
from services.omnichannel.kiotviet_connection_service import KiotVietConnectionInput, KiotVietConnectionService
from services.omnichannel.providers.registry import ChannelProviderRegistry


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
    access_token: str = Field(min_length=1)
    api_version: str = Field(default="v23.0", min_length=1, max_length=32)
    enabled: bool = True


class ChannelUpdatePayload(BaseModel):
    channel_type: str | None = Field(default=None, min_length=1, max_length=60)
    app_id: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    external_resource_id: str | None = Field(default=None, min_length=1, max_length=255)
    verify_token: str | None = Field(default=None, min_length=1)
    client_secret: str | None = Field(default=None, min_length=1)
    access_token: str | None = Field(default=None, min_length=1)
    api_version: str | None = Field(default=None, min_length=1, max_length=32)
    enabled: bool | None = None

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


register_schema_models(
    console_ns,
    MessengerChannelCreatePayload,
    MessengerChannelUpdatePayload,
    ChannelCreatePayload,
    ChannelUpdatePayload,
    KiotVietConnectionCreatePayload,
    KiotVietConnectionUpdatePayload,
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

