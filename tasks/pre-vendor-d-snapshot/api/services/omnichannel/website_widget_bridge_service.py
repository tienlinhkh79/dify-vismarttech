"""Mirror published web-app chat turns into omnichannel inbox + Mini CRM."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.model import App, EndUser, Message, Site
from models.trigger import (
    OmniChannelConfig,
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
    OmniChannelType,
)
from services.omnichannel.omnichannel_contact_hints import extract_display_name_from_text, normalize_display_name
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService

logger = logging.getLogger(__name__)


class WebsiteWidgetBridgeService:
    @staticmethod
    def _external_user_id(end_user: EndUser) -> str:
        session_id = (end_user.session_id or "").strip()
        if session_id:
            return session_id
        return str(end_user.id)

    @classmethod
    def find_channel_for_app(cls, *, tenant_id: str, app_id: str) -> OmniChannelConfig | None:
        with Session(db.engine, expire_on_commit=False) as session:
            return session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.app_id == app_id,
                    OmniChannelConfig.channel_type == OmniChannelType.WEBSITE_WIDGET,
                    OmniChannelConfig.enabled.is_(True),
                )
            )

    @classmethod
    def find_channel_for_site_code(cls, site_code: str) -> OmniChannelConfig | None:
        token = (site_code or "").strip()
        if not token:
            return None
        with Session(db.engine, expire_on_commit=False) as session:
            return session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.page_id == token,
                    OmniChannelConfig.channel_type == OmniChannelType.WEBSITE_WIDGET,
                    OmniChannelConfig.enabled.is_(True),
                )
            )

    @classmethod
    def _record(
        cls,
        *,
        config: OmniChannelConfig,
        end_user: EndUser,
        direction: OmniChannelMessageDirection,
        content: str,
        web_conversation_id: str | None,
        web_message_id: str | None,
    ) -> None:
        if not content.strip():
            return
        participant_name = normalize_display_name(end_user.name)
        if direction == OmniChannelMessageDirection.INBOUND and not participant_name:
            participant_name = extract_display_name_from_text(content)
        metadata: dict[str, Any] = {
            "web_conversation_id": web_conversation_id or "",
            "web_message_id": web_message_id or "",
            "end_user_id": str(end_user.id),
        }
        payload: MessageWritePayload = {
            "tenant_id": config.tenant_id,
            "channel_id": config.channel_id,
            "external_user_id": cls._external_user_id(end_user),
            "direction": direction,
            "source": OmniChannelMessageSource.WEB_APP,
            "content": content.strip(),
            "external_message_id": web_message_id,
            "attachments": [],
            "metadata": metadata,
            "participant_display_name": participant_name,
            "participant_profile_pic_url": None,
            "created_at": None,
        }
        try:
            OmnichannelOpsService.record_message(payload)
        except Exception:
            logger.exception(
                "website_widget bridge record failed channel=%s direction=%s",
                config.channel_id,
                direction.value,
            )

    @classmethod
    def record_inbound_user_message(
        cls,
        *,
        app_model: App,
        end_user: EndUser,
        query: str,
        web_conversation_id: str | None,
        display_query: str | None = None,
    ) -> None:
        config = cls.find_channel_for_app(tenant_id=app_model.tenant_id, app_id=str(app_model.id))
        if not config:
            return
        visible = (display_query or query).strip()
        cls._record(
            config=config,
            end_user=end_user,
            direction=OmniChannelMessageDirection.INBOUND,
            content=visible,
            web_conversation_id=web_conversation_id,
            web_message_id=None,
        )

    @classmethod
    def record_outbound_assistant_message(
        cls,
        *,
        app_model: App,
        end_user: EndUser,
        answer: str,
        web_conversation_id: str | None,
        web_message_id: str | None,
    ) -> None:
        config = cls.find_channel_for_app(tenant_id=app_model.tenant_id, app_id=str(app_model.id))
        if not config:
            return
        cls._record(
            config=config,
            end_user=end_user,
            direction=OmniChannelMessageDirection.OUTBOUND,
            content=answer,
            web_conversation_id=web_conversation_id,
            web_message_id=web_message_id,
        )

    @staticmethod
    def _fetch_message_text(message_id: str) -> tuple[str, str]:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(select(Message).where(Message.id == message_id))
        if not row:
            return "", ""
        return (row.answer or "").strip(), str(row.conversation_id or "")

    @classmethod
    def sync_blocking_turn(
        cls,
        *,
        app_model: App,
        end_user: EndUser,
        query: str,
        web_conversation_id: str | None,
        response: Mapping[str, Any] | Any,
        display_query: str | None = None,
    ) -> None:
        cls.record_inbound_user_message(
            app_model=app_model,
            end_user=end_user,
            query=query,
            display_query=display_query,
            web_conversation_id=web_conversation_id,
        )
        answer = ""
        message_id = ""
        conv_id = web_conversation_id
        if isinstance(response, Mapping):
            data = response.get("data")
            if isinstance(data, Mapping):
                answer = str(data.get("answer") or "").strip()
                message_id = str(data.get("id") or data.get("message_id") or "").strip()
                if not conv_id:
                    conv_id = str(data.get("conversation_id") or "").strip() or None
            if not answer:
                answer = str(response.get("answer") or "").strip()
            if not message_id:
                message_id = str(response.get("id") or response.get("message_id") or "").strip()
        else:
            data = getattr(response, "data", None)
            if data is not None:
                answer = str(getattr(data, "answer", "") or "").strip()
                message_id = str(getattr(data, "id", "") or getattr(data, "message_id", "") or "").strip()
                if not conv_id:
                    conv_id = str(getattr(data, "conversation_id", "") or "").strip() or None
        if not answer and message_id:
            answer, conv_from_msg = cls._fetch_message_text(message_id)
            if not conv_id and conv_from_msg:
                conv_id = conv_from_msg
        cls.record_outbound_assistant_message(
            app_model=app_model,
            end_user=end_user,
            answer=answer,
            web_conversation_id=conv_id,
            web_message_id=message_id or None,
        )

    @classmethod
    def wrap_streaming_response(
        cls,
        stream: Generator[str, None, None],
        *,
        app_model: App,
        end_user: EndUser,
        query: str,
        web_conversation_id: str | None,
        display_query: str | None = None,
    ) -> Generator[str, None, None]:
        cls.record_inbound_user_message(
            app_model=app_model,
            end_user=end_user,
            query=query,
            display_query=display_query,
            web_conversation_id=web_conversation_id,
        )
        message_id = ""
        conv_id = web_conversation_id
        for chunk in stream:
            yield chunk
            if not isinstance(chunk, str):
                continue
            for line in chunk.splitlines():
                if not line.startswith("data:"):
                    continue
                payload_text = line[5:].strip()
                if not payload_text or payload_text == "[DONE]":
                    continue
                try:
                    payload = json.loads(payload_text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                event = str(payload.get("event") or "").strip()
                if event == "message_end":
                    message_id = str(payload.get("id") or "").strip()
                    if not conv_id:
                        conv_id = str(payload.get("conversation_id") or "").strip() or None
        if message_id:
            answer, conv_from_msg = cls._fetch_message_text(message_id)
            if not conv_id and conv_from_msg:
                conv_id = conv_from_msg
            cls.record_outbound_assistant_message(
                app_model=app_model,
                end_user=end_user,
                answer=answer,
                web_conversation_id=conv_id,
                web_message_id=message_id,
            )

    @classmethod
    def resolve_site_code_for_app(cls, app_id: str) -> str | None:
        with Session(db.engine, expire_on_commit=False) as session:
            site = session.scalar(select(Site).where(Site.app_id == app_id))
        if not site or not (site.code or "").strip():
            return None
        return site.code.strip()
