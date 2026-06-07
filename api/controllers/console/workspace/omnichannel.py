from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from flask import Response, request
from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator, model_validator
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

import services
from controllers.common.errors import (
    BlockedFileExtensionError,
    FilenameNotExistsError,
    FileTooLargeError,
    NoFileUploadedError,
    TooManyFilesError,
    UnsupportedFileTypeError,
)
from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from extensions.ext_redis import get_pubsub_broadcast_channel
from libs.login import current_account_with_tenant, login_required
from models.account import AccountStatus
from services.omnichannel.channel_management_service import ChannelInput, ChannelManagementService
from services.omnichannel.kiotviet_connection_service import KiotVietConnectionInput, KiotVietConnectionService
from services.omnichannel.omnichannel_agent_reply_service import OmnichannelAgentReplyService
from services.omnichannel.omnichannel_canned_response_service import OmnichannelCannedResponseService
from services.omnichannel.omnichannel_media_storage_service import OmnichannelMediaStorageService
from services.omnichannel.omnichannel_ops_service import OmnichannelOpsService
from services.omnichannel.omnichannel_realtime import omnichannel_pubsub_topic
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
    zalo_auto_reply_enabled: bool = False
    zalo_info_card_enabled: bool = False
    zalo_info_card_title: str | None = Field(default=None, max_length=255)
    zalo_info_card_subtitle: str | None = Field(default=None, max_length=512)
    zalo_info_card_image_url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_access_token_by_channel(self):
        if self.channel_type in ("zalo_oa", "zalo_personal", "facebook_messenger"):
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
    zalo_auto_reply_enabled: bool | None = None
    zalo_info_card_enabled: bool | None = None
    zalo_info_card_title: str | None = Field(default=None, max_length=255)
    zalo_info_card_subtitle: str | None = Field(default=None, max_length=512)
    zalo_info_card_image_url: str | None = Field(default=None, max_length=2048)

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


class OmnichannelConversationCreatePayload(BaseModel):
    external_user_id: str = Field(min_length=1, max_length=255)


class OmnichannelAgentMessagePayload(BaseModel):
    text: str = Field(default="", max_length=8000)
    attachment_url: str | None = Field(default=None, max_length=2048)
    attachment_type: Literal["image", "video", "audio", "file"] | None = None
    quote_message_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def validate_body(self) -> OmnichannelAgentMessagePayload:
        if not self.text.strip() and not (self.attachment_url or "").strip():
            raise ValueError("text or attachment_url is required")
        url = (self.attachment_url or "").strip()
        if url and self.attachment_type is None:
            raise ValueError("attachment_type is required when attachment_url is set")
        return self


class OmnichannelConversationListPayload(ChannelTimeFilterPayload):
    channel_id: str | None = Field(default=None, max_length=255)
    status: Literal["open", "resolved", "pending", "snoozed"] | None = None
    assignee_account_id: str | None = Field(default=None, max_length=36)
    unassigned_only: bool = False


class OmnichannelConversationUpdatePayload(BaseModel):
    status: Literal["open", "resolved", "pending", "snoozed"] | None = None
    assignee_account_id: str | None = Field(default=None, max_length=36)
    clear_assignee: bool = False


class OmnichannelInternalNotePayload(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class OmnichannelMarkSeenPayload(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=36)


class OmnichannelCannedResponsePayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=8000)
    shortcut: str | None = Field(default=None, max_length=64)


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
    OmnichannelAgentMessagePayload,
    OmnichannelConversationCreatePayload,
    OmnichannelConversationListPayload,
    OmnichannelConversationUpdatePayload,
    OmnichannelInternalNotePayload,
    OmnichannelMarkSeenPayload,
    OmnichannelCannedResponsePayload,
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
        raw_flag = (request.args.get("include_branding") or "").strip().lower()
        include_branding = raw_flag in {"1", "true", "yes", "on"}
        channels = ChannelManagementService.list_channels(tenant_id, include_branding=include_branding)
        return jsonable_encoder({"data": channels})

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
        except ValueError as e:
            if str(e) == "Channel not found":
                raise NotFound("Channel not found") from e
            return {"error": str(e)}, 400
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


@console_ns.route("/workspaces/current/channels/<string:channel_id>/stream")
class ChannelOmnichannelStreamApi(Resource):
    """Server-Sent Events stream: Redis pub/sub pushes when omnichannel data changes (webhook, sync, profile)."""

    @setup_required
    def get(self, channel_id: str):
        try:
            account, tenant_id = current_account_with_tenant()
        except ValueError as exc:
            raise Unauthorized("Unauthorized.") from exc
        if account.status == AccountStatus.UNINITIALIZED:
            raise Unauthorized("Account is not initialized.")
        if ChannelManagementService.get_channel(tenant_id, channel_id) is None:
            raise NotFound("Channel not found")

        topic_name = omnichannel_pubsub_topic(tenant_id=tenant_id, channel_id=channel_id)

        def event_stream():
            broadcast = get_pubsub_broadcast_channel()
            subscription = broadcast.topic(topic_name).subscribe()
            with subscription:
                yield f"data: {json.dumps({'type': 'connected', 'channel_id': channel_id}, separators=(',', ':'))}\n\n"
                while True:
                    item = subscription.receive(timeout=12.0)
                    if item is None:
                        yield ": ping\n\n"
                        continue
                    try:
                        text = item.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    yield f"data: {text}\n\n"

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


@console_ns.route("/workspaces/current/omnichannel/conversations")
class OmnichannelConversationCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        filter_payload = OmnichannelConversationListPayload.model_validate(request.args.to_dict())
        try:
            result = OmnichannelOpsService.list_conversations(
                tenant_id=tenant_id,
                channel_id=(filter_payload.channel_id or "").strip() or None,
                since=filter_payload.since,
                until=filter_payload.until,
                cursor=filter_payload.cursor,
                limit=filter_payload.limit,
                status=filter_payload.status,
                assignee_account_id=filter_payload.assignee_account_id,
                unassigned_only=filter_payload.unassigned_only,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/channels/<string:channel_id>/conversations")
class ChannelConversationCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        filter_payload = ChannelTimeFilterPayload.model_validate(request.args.to_dict())
        status = (request.args.get("status") or "").strip() or None
        assignee_account_id = (request.args.get("assignee_account_id") or "").strip() or None
        unassigned_only = (request.args.get("unassigned_only") or "").strip().lower() in {"1", "true", "yes"}
        try:
            result = OmnichannelOpsService.list_conversations(
                tenant_id=tenant_id,
                channel_id=channel_id,
                since=filter_payload.since,
                until=filter_payload.until,
                cursor=filter_payload.cursor,
                limit=filter_payload.limit,
                status=status,
                assignee_account_id=assignee_account_id,
                unassigned_only=unassigned_only,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder(result)

    @console_ns.expect(console_ns.models[OmnichannelConversationCreatePayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = OmnichannelConversationCreatePayload.model_validate(console_ns.payload or {})
        try:
            data = OmnichannelOpsService.create_or_get_conversation(
                tenant_id=tenant_id,
                channel_id=channel_id,
                external_user_id=payload.external_user_id,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise NotFound(msg) from exc
            raise BadRequest(msg) from exc
        return jsonable_encoder({"data": data}), 201


@console_ns.route(
    "/workspaces/current/channels/<string:channel_id>/conversations/<string:conversation_id>/refresh-participant"
)
class ChannelConversationParticipantRefreshApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            data = OmnichannelOpsService.refresh_messenger_conversation_participant(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise NotFound(msg) from exc
            raise BadRequest(msg) from exc
        return jsonable_encoder({"data": data}), 200


@console_ns.route("/workspaces/current/omnichannel/media-upload")
class OmnichannelMediaUploadApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        current_user, _ = current_account_with_tenant()
        if "file" not in request.files:
            raise NoFileUploadedError()

        if len(request.files) > 1:
            raise TooManyFilesError()
        file = request.files["file"]
        if not file.filename:
            raise FilenameNotExistsError

        try:
            data = OmnichannelMediaStorageService.upload(
                filename=file.filename,
                content=file.read(),
                mimetype=file.mimetype or "",
                user=current_user,
            )
        except services.errors.file.FileTooLargeError as file_too_large_error:
            raise FileTooLargeError(file_too_large_error.description) from file_too_large_error
        except services.errors.file.UnsupportedFileTypeError as exc:
            raise UnsupportedFileTypeError() from exc
        except services.errors.file.BlockedFileExtensionError as blocked_extension_error:
            raise BlockedFileExtensionError(blocked_extension_error.description) from blocked_extension_error
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc

        return jsonable_encoder({"data": data}), 201


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

    @console_ns.expect(console_ns.models[OmnichannelAgentMessagePayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = OmnichannelAgentMessagePayload.model_validate(console_ns.payload or {})
        try:
            data = OmnichannelAgentReplyService.send_reply(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
                text=payload.text,
                attachment_url=payload.attachment_url,
                attachment_type=payload.attachment_type,
                quote_message_id=payload.quote_message_id,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201


@console_ns.route(
    "/workspaces/current/channels/<string:channel_id>/conversations/<string:conversation_id>"
)
class ChannelConversationApi(Resource):
    @console_ns.expect(console_ns.models[OmnichannelConversationUpdatePayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, channel_id: str, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = OmnichannelConversationUpdatePayload.model_validate(console_ns.payload or {})
        try:
            data = OmnichannelOpsService.update_conversation(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
                status=payload.status,
                assignee_account_id=payload.assignee_account_id,
                clear_assignee=payload.clear_assignee,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise NotFound(msg) from exc
            raise BadRequest(msg) from exc
        return jsonable_encoder({"data": data})


@console_ns.route(
    "/workspaces/current/channels/<string:channel_id>/conversations/<string:conversation_id>/mark-seen"
)
class ChannelConversationMarkSeenApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            data = OmnichannelOpsService.mark_conversation_seen(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise NotFound(msg) from exc
            raise BadRequest(msg) from exc
        return jsonable_encoder({"data": data})


@console_ns.route("/workspaces/current/channels/<string:channel_id>/conversations/seen")
class ChannelConversationMarkSeenLegacyApi(Resource):
    """Legacy path used by older web builds: conversation id in JSON body."""

    @console_ns.expect(console_ns.models[OmnichannelMarkSeenPayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        payload = OmnichannelMarkSeenPayload.model_validate(console_ns.payload or {})
        try:
            data = OmnichannelOpsService.mark_conversation_seen(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=payload.conversation_id,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise NotFound(msg) from exc
            raise BadRequest(msg) from exc
        return jsonable_encoder({"data": data})


@console_ns.route(
    "/workspaces/current/channels/<string:channel_id>/conversations/<string:conversation_id>/internal-notes"
)
class ChannelConversationInternalNoteApi(Resource):
    @console_ns.expect(console_ns.models[OmnichannelInternalNotePayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, channel_id: str, conversation_id: str):
        account, tenant_id = current_account_with_tenant()
        payload = OmnichannelInternalNotePayload.model_validate(console_ns.payload or {})
        try:
            data = OmnichannelOpsService.add_internal_note(
                tenant_id=tenant_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
                text=payload.text,
                author_account_id=account.id,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201


@console_ns.route("/workspaces/current/omnichannel/canned-responses")
class OmnichannelCannedResponseCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        rows = OmnichannelCannedResponseService.list_responses(tenant_id=tenant_id)
        return jsonable_encoder({"data": rows})

    @console_ns.expect(console_ns.models[OmnichannelCannedResponsePayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        _, tenant_id = current_account_with_tenant()
        payload = OmnichannelCannedResponsePayload.model_validate(console_ns.payload or {})
        try:
            row = OmnichannelCannedResponseService.create_response(
                tenant_id=tenant_id,
                title=payload.title,
                content=payload.content,
                shortcut=payload.shortcut,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": row}), 201


@console_ns.route("/workspaces/current/omnichannel/canned-responses/<string:response_id>")
class OmnichannelCannedResponseApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def delete(self, response_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            OmnichannelCannedResponseService.delete_response(tenant_id=tenant_id, response_id=response_id)
        except ValueError as exc:
            raise NotFound(str(exc)) from exc
        return {"result": "success"}, 200


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


@console_ns.route("/workspaces/current/channels/<string:channel_id>/zalo-bridge-jobs/failed")
class ChannelZaloBridgeFailedJobsApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def get(self, channel_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        from services.omnichannel.zalo_bridge_job_service import ZaloBridgeJobService

        limit = min(int(request.args.get("limit", 50)), 200)
        jobs = ZaloBridgeJobService.list_failed(channel_id=channel_id, limit=limit)
        return jsonable_encoder({"data": jobs})


@console_ns.route("/workspaces/current/channels/<string:channel_id>/zalo-bridge-jobs/<string:job_id>/retry")
class ChannelZaloBridgeJobRetryApi(Resource):
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self, channel_id: str, job_id: str):
        _, tenant_id = current_account_with_tenant()
        channel = ChannelManagementService.get_channel(tenant_id, channel_id)
        if not channel:
            raise NotFound("Channel not found")
        from services.omnichannel.zalo_bridge_job_service import ZaloBridgeJobService
        from tasks.omnichannel_tasks import process_zalo_bridge_worker

        if not ZaloBridgeJobService.retry_failed(job_id):
            raise NotFound("Failed job not found")
        process_zalo_bridge_worker.delay()
        return {"result": "success"}, 202


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

