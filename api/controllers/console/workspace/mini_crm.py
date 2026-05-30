from __future__ import annotations

from flask import Response, request
from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator, model_validator
from werkzeug.exceptions import BadRequest, NotFound

from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from libs.login import current_account_with_tenant, login_required
from models.trigger import OmniChannelCrmLeadStage
from services.omnichannel.mini_crm_analytics_service import MiniCrmAnalyticsService
from services.omnichannel.mini_crm_service import MiniCrmService


class MiniCrmLeadPatchPayload(BaseModel):
    stage: str | None = Field(default=None, max_length=32)
    owner_account_id: str | None = Field(default=None, max_length=36)
    notes: str | None = Field(default=None, max_length=65535)
    notes_append: str | None = Field(default=None, max_length=4000)
    source_override: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = Field(default=None, max_length=20)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def notes_exclusive(self) -> MiniCrmLeadPatchPayload:
        if self.notes is not None and self.notes_append is not None:
            raise ValueError("Provide either notes or notes_append, not both")
        return self

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


class MiniCrmLeadBulkPatchPayload(BaseModel):
    conversation_ids: list[str] = Field(min_length=1, max_length=200)
    stage: str | None = Field(default=None, max_length=32)
    owner_account_id: str | None = Field(default=None, max_length=36)
    tags: list[str] | None = Field(default=None, max_length=20)

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


register_schema_models(console_ns, MiniCrmLeadPatchPayload, MiniCrmLeadBulkPatchPayload)


def _list_filters_from_request() -> tuple[str | None, str | None, str | None]:
    channel_type = request.args.get("channel_type") or None
    stage = request.args.get("stage") or None
    search_query = request.args.get("q") or None
    return channel_type, stage, search_query


def _pagination_from_request() -> tuple[int, int]:
    try:
        page_size = int(request.args.get("limit") or request.args.get("page_size") or 25)
    except ValueError:
        page_size = 25
    page_size = min(max(page_size, 1), 200)

    page_arg = request.args.get("page")
    if page_arg is not None:
        try:
            page_number = max(int(page_arg), 1)
        except ValueError:
            page_number = 1
        return (page_number - 1) * page_size, page_size

    try:
        page_offset = int(request.args.get("offset") or 0)
    except ValueError:
        page_offset = 0
    return max(page_offset, 0), page_size


@console_ns.route("/workspaces/current/mini-crm/leads")
class MiniCrmLeadCollectionApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        channel_type, stage, search_query = _list_filters_from_request()
        page_offset, page_size = _pagination_from_request()
        result = MiniCrmService.list_leads(
            tenant_id=tenant_id,
            channel_type=channel_type,
            stage=stage,
            search_query=search_query,
            page_offset=page_offset,
            page_size=page_size,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/leads/export")
class MiniCrmLeadExportApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        channel_type, stage, search_query = _list_filters_from_request()
        csv_content = MiniCrmService.export_leads_csv(
            tenant_id=tenant_id,
            channel_type=channel_type,
            stage=stage,
            search_query=search_query,
        )
        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="mini-crm-leads.csv"'},
        )


@console_ns.route("/workspaces/current/mini-crm/leads/bulk")
class MiniCrmLeadBulkApi(Resource):
    @console_ns.expect(console_ns.models[MiniCrmLeadBulkPatchPayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self):
        _, tenant_id = current_account_with_tenant()
        try:
            payload = MiniCrmLeadBulkPatchPayload.model_validate(console_ns.payload or {})
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        body = payload.model_dump(exclude_unset=True)
        conversation_ids = body.pop("conversation_ids", [])
        if not body:
            raise BadRequest("At least one field besides conversation_ids must be provided")
        bulk_kwargs: dict[str, object] = {
            "tenant_id": tenant_id,
            "conversation_ids": conversation_ids,
        }
        if "stage" in body:
            bulk_kwargs["stage"] = body["stage"]
        if "owner_account_id" in body:
            bulk_kwargs["owner_account_id"] = body["owner_account_id"]
        if "tags" in body:
            bulk_kwargs["tags"] = body["tags"]
        try:
            result = MiniCrmService.bulk_patch_leads(**bulk_kwargs)
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/leads/<string:conversation_id>")
class MiniCrmLeadApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        lead = MiniCrmService.get_lead(tenant_id=tenant_id, conversation_id=conversation_id)
        if not lead:
            raise NotFound("Conversation not found")
        return jsonable_encoder({"data": lead})

    @console_ns.expect(console_ns.models[MiniCrmLeadPatchPayload.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, conversation_id: str):
        account, tenant_id = current_account_with_tenant()
        try:
            payload = MiniCrmLeadPatchPayload.model_validate(console_ns.payload or {})
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        body = payload.model_dump(exclude_unset=True)
        if not body:
            raise BadRequest("At least one field must be provided")
        lead_patch_call_kwargs: dict[str, object] = {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "actor_account_id": account.id,
        }
        for field_name in (
            "stage",
            "owner_account_id",
            "notes",
            "notes_append",
            "source_override",
            "tags",
            "contact_phone",
            "contact_email",
        ):
            if field_name in body:
                lead_patch_call_kwargs[field_name] = body[field_name]
        try:
            updated = MiniCrmService.patch_lead(**lead_patch_call_kwargs)
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        if not updated:
            raise NotFound("Conversation not found")
        return jsonable_encoder({"data": updated})


@console_ns.route("/workspaces/current/mini-crm/leads/<string:conversation_id>/timeline")
class MiniCrmLeadTimelineApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, conversation_id: str):
        _, tenant_id = current_account_with_tenant()
        try:
            limit = int(request.args.get("limit") or 50)
        except ValueError:
            limit = 50
        result = MiniCrmAnalyticsService.list_timeline(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=limit,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/analytics/funnel")
class MiniCrmFunnelAnalyticsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        channel_type = request.args.get("channel_type") or None
        try:
            period_days = int(request.args.get("period_days") or 30)
        except ValueError:
            period_days = 30
        result = MiniCrmAnalyticsService.get_funnel_analytics(
            tenant_id=tenant_id,
            channel_type=channel_type,
            period_days=period_days,
        )
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/remarketing/segments")
class MiniCrmRemarketingSegmentsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        _, tenant_id = current_account_with_tenant()
        channel_type = request.args.get("channel_type") or None
        base = MiniCrmAnalyticsService.list_remarketing_segments()
        enriched: list[dict[str, object]] = []
        for segment in base.get("data") or []:
            segment_key = str(segment.get("key") or "")
            if not segment_key:
                continue
            try:
                page = MiniCrmAnalyticsService.get_remarketing_segment_leads(
                    tenant_id=tenant_id,
                    segment_key=segment_key,
                    channel_type=channel_type,
                    page_offset=0,
                    page_size=1,
                )
                lead_count = page.get("total") or 0
            except ValueError:
                lead_count = 0
            enriched.append({**segment, "lead_count": lead_count})
        return jsonable_encoder({"data": enriched})


@console_ns.route("/workspaces/current/mini-crm/remarketing/segments/<string:segment_key>/leads")
class MiniCrmRemarketingSegmentLeadsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, segment_key: str):
        _, tenant_id = current_account_with_tenant()
        channel_type = request.args.get("channel_type") or None
        try:
            page_offset = int(request.args.get("offset") or 0)
        except ValueError:
            page_offset = 0
        try:
            page_size = int(request.args.get("limit") or 50)
        except ValueError:
            page_size = 50
        try:
            result = MiniCrmAnalyticsService.get_remarketing_segment_leads(
                tenant_id=tenant_id,
                segment_key=segment_key,
                channel_type=channel_type,
                page_offset=page_offset,
                page_size=page_size,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder(result)


@console_ns.route("/workspaces/current/mini-crm/remarketing/segments/<string:segment_key>/export")
class MiniCrmRemarketingSegmentExportApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, segment_key: str):
        _, tenant_id = current_account_with_tenant()
        channel_type = request.args.get("channel_type") or None
        try:
            csv_content = MiniCrmAnalyticsService.export_remarketing_segment_csv(
                tenant_id=tenant_id,
                segment_key=segment_key,
                channel_type=channel_type,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="mini-crm-segment-{segment_key}.csv"'},
        )
