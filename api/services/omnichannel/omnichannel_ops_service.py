from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
import logging
from typing import Any, NotRequired, TypedDict

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from core.helper.ssrf_proxy import ssrf_proxy
from extensions.ext_database import db
from models.trigger import (
    OmniChannelConfig,
    OmniChannelConversation,
    OmniChannelMessage,
    OmniChannelMessageDirection,
    OmniChannelMessageSource,
    OmniChannelSyncJob,
    OmniChannelSyncJobStatus,
    OmniChannelType,
)
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_graph_profile import extract_graph_picture_url, fetch_messenger_user_profile
from services.omnichannel.omnichannel_realtime import publish_omnichannel_change

logger = logging.getLogger(__name__)


class MessageWritePayload(TypedDict):
    tenant_id: str
    channel_id: str
    external_user_id: str
    direction: OmniChannelMessageDirection
    source: OmniChannelMessageSource
    content: str
    external_message_id: str | None
    attachments: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime | None
    participant_display_name: NotRequired[str | None]
    participant_profile_pic_url: NotRequired[str | None]
    channel_actor_name: NotRequired[str | None]
    channel_actor_picture_url: NotRequired[str | None]


class OmnichannelOpsService:
    _DEFAULT_LIMIT = 20
    _MAX_LIMIT = 100
    _CHANNEL_TO_WEBHOOK_PROVIDER = {
        OmniChannelType.FACEBOOK_MESSENGER: "messenger",
        OmniChannelType.INSTAGRAM_DM: "messenger",
        OmniChannelType.TIKTOK_MESSAGING: "messenger",
        OmniChannelType.ZALO_OA: "zalo",
    }
    _MAX_SYNC_MESSAGES = 500
    _GRAPH_PAGE_LIMIT = 50

    @staticmethod
    def _parse_cursor(cursor: str | None) -> int:
        if not cursor:
            return 0
        try:
            value = int(cursor)
        except ValueError:
            return 0
        return max(value, 0)

    @classmethod
    def _normalize_limit(cls, limit: int | None) -> int:
        if not limit:
            return cls._DEFAULT_LIMIT
        return min(max(limit, 1), cls._MAX_LIMIT)

    @staticmethod
    def _normalize_dt(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    @classmethod
    def _conversation_query(
        cls,
        tenant_id: str,
        channel_id: str,
        since: datetime | None,
        until: datetime | None,
    ) -> Select[tuple[OmniChannelConversation]]:
        query = select(OmniChannelConversation).where(
            OmniChannelConversation.tenant_id == tenant_id,
            OmniChannelConversation.channel_id == channel_id,
        )
        if since is not None:
            query = query.where(OmniChannelConversation.last_message_at >= since)
        if until is not None:
            query = query.where(OmniChannelConversation.last_message_at <= until)
        return query.order_by(OmniChannelConversation.last_message_at.desc().nullslast(), OmniChannelConversation.id.desc())

    @classmethod
    def list_conversations(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        since: datetime | None,
        until: datetime | None,
        cursor: str | None,
        limit: int | None,
    ) -> dict[str, Any]:
        cursor_value = cls._parse_cursor(cursor)
        page_size = cls._normalize_limit(limit)
        since = cls._normalize_dt(since)
        until = cls._normalize_dt(until)

        with Session(db.engine, expire_on_commit=False) as session:
            query = cls._conversation_query(tenant_id, channel_id, since, until).offset(cursor_value).limit(page_size + 1)
            rows = session.scalars(query).all()

        has_more = len(rows) > page_size
        data = rows[:page_size]
        next_cursor = str(cursor_value + page_size) if has_more else None
        return {
            "data": [
                {
                    "id": item.id,
                    "external_user_id": item.external_user_id,
                    "participant_display_name": item.participant_display_name,
                    "participant_profile_pic_url": item.participant_profile_pic_url,
                    "last_message_at": item.last_message_at,
                    "channel_id": item.channel_id,
                    "channel_type": item.channel_type.value,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in data
            ],
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    @classmethod
    def refresh_messenger_conversation_participant(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Re-fetch Messenger User Profile (PSID) from Graph and persist on the conversation row."""
        messenger_cfg = ChannelConfigService.get_messenger_channel_config(channel_id)
        if not messenger_cfg or messenger_cfg["tenant_id"] != tenant_id:
            raise ValueError("Channel not found")

        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
            if not config:
                raise ValueError("Channel not found")
            if config.channel_type != OmniChannelType.FACEBOOK_MESSENGER:
                raise ValueError(
                    "Participant refresh is only supported for facebook_messenger channels"
                )
            conv = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conv:
                raise ValueError("Conversation not found")
            psid = conv.external_user_id

        prof = fetch_messenger_user_profile(
            psid=psid,
            access_token=messenger_cfg["page_access_token"],
            graph_version=messenger_cfg["graph_api_version"],
        )
        pname = str(prof.get("name") or "").strip()
        purl = str(prof.get("profile_pic") or "").strip()
        if not pname and not purl:
            logger.info(
                "Messenger participant refresh: Graph returned no name or picture conversation_id=%s psid=%s",
                conversation_id,
                psid,
            )

        with Session(db.engine, expire_on_commit=False) as session:
            conv = session.scalar(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                    OmniChannelConversation.id == conversation_id,
                )
            )
            if not conv:
                raise ValueError("Conversation not found")
            if pname:
                conv.participant_display_name = pname
            if purl:
                conv.participant_profile_pic_url = purl
            session.commit()
            session.refresh(conv)
            out = {
                "id": conv.id,
                "external_user_id": conv.external_user_id,
                "participant_display_name": conv.participant_display_name,
                "participant_profile_pic_url": conv.participant_profile_pic_url,
                "last_message_at": conv.last_message_at,
                "channel_id": conv.channel_id,
                "channel_type": conv.channel_type.value,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
            }
        publish_omnichannel_change(
            tenant_id=tenant_id,
            channel_id=channel_id,
            conversation_id=str(out["id"]),
            kind="conversations",
        )
        return out

    @classmethod
    def list_messages(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        conversation_id: str,
        since: datetime | None,
        until: datetime | None,
        cursor: str | None,
        limit: int | None,
    ) -> dict[str, Any]:
        cursor_value = cls._parse_cursor(cursor)
        page_size = cls._normalize_limit(limit)
        since = cls._normalize_dt(since)
        until = cls._normalize_dt(until)

        with Session(db.engine, expire_on_commit=False) as session:
            query = select(OmniChannelMessage).where(
                OmniChannelMessage.tenant_id == tenant_id,
                OmniChannelMessage.channel_id == channel_id,
                OmniChannelMessage.conversation_id == conversation_id,
            )
            if since is not None:
                query = query.where(OmniChannelMessage.created_at >= since)
            if until is not None:
                query = query.where(OmniChannelMessage.created_at <= until)
            query = query.order_by(OmniChannelMessage.created_at.desc(), OmniChannelMessage.id.desc())
            rows = session.scalars(query.offset(cursor_value).limit(page_size + 1)).all()

        has_more = len(rows) > page_size
        data = rows[:page_size]
        next_cursor = str(cursor_value + page_size) if has_more else None
        return {
            "data": [
                {
                    "id": item.id,
                    "conversation_id": item.conversation_id,
                    "external_user_id": item.external_user_id,
                    "external_message_id": item.external_message_id,
                    "direction": item.direction.value,
                    "source": item.source.value,
                    "content": item.content,
                    "attachments": item.attachments,
                    "metadata": item.message_metadata,
                    "sender_display_name": (item.message_metadata or {}).get("sender_display_name"),
                    "sender_profile_pic_url": (item.message_metadata or {}).get("sender_profile_pic_url"),
                    "channel_actor_name": (item.message_metadata or {}).get("channel_actor_name"),
                    "channel_actor_picture_url": (item.message_metadata or {}).get("channel_actor_picture_url"),
                    "created_at": item.created_at,
                }
                for item in data
            ],
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    @classmethod
    def _get_channel_type(cls, session: Session, tenant_id: str, channel_id: str) -> OmniChannelType:
        config = session.scalar(
            select(OmniChannelConfig).where(
                OmniChannelConfig.tenant_id == tenant_id,
                OmniChannelConfig.channel_id == channel_id,
            )
        )
        if not config:
            raise ValueError("Channel not found")
        return config.channel_type

    @classmethod
    def _get_or_create_conversation(
        cls,
        *,
        session: Session,
        tenant_id: str,
        channel_id: str,
        channel_type: OmniChannelType,
        external_user_id: str,
        last_message_at: datetime,
    ) -> OmniChannelConversation:
        row = session.scalar(
            select(OmniChannelConversation).where(
                OmniChannelConversation.tenant_id == tenant_id,
                OmniChannelConversation.channel_id == channel_id,
                OmniChannelConversation.external_user_id == external_user_id,
            )
        )
        if row:
            row.last_message_at = last_message_at
            return row

        row = OmniChannelConversation(
            tenant_id=tenant_id,
            channel_id=channel_id,
            channel_type=channel_type,
            external_user_id=external_user_id,
            last_message_at=last_message_at,
        )
        session.add(row)
        session.flush()
        return row

    @classmethod
    def record_message(cls, payload: MessageWritePayload) -> dict[str, Any]:
        created_at = cls._normalize_dt(payload.get("created_at")) or datetime.utcnow()
        metadata = dict(payload.get("metadata") or {})
        pname = str(payload.get("participant_display_name") or "").strip()
        purl = str(payload.get("participant_profile_pic_url") or "").strip()
        caname = str(payload.get("channel_actor_name") or "").strip()
        caurl = str(payload.get("channel_actor_picture_url") or "").strip()
        if pname:
            metadata["sender_display_name"] = pname
        if purl:
            metadata["sender_profile_pic_url"] = purl
        if caname:
            metadata["channel_actor_name"] = caname
        if caurl:
            metadata["channel_actor_picture_url"] = caurl

        direction = payload["direction"]
        with Session(db.engine, expire_on_commit=False) as session:
            channel_type = cls._get_channel_type(session, payload["tenant_id"], payload["channel_id"])
            conversation = cls._get_or_create_conversation(
                session=session,
                tenant_id=payload["tenant_id"],
                channel_id=payload["channel_id"],
                channel_type=channel_type,
                external_user_id=payload["external_user_id"],
                last_message_at=created_at,
            )
            if direction == OmniChannelMessageDirection.INBOUND:
                if pname:
                    conversation.participant_display_name = pname
                if purl:
                    conversation.participant_profile_pic_url = purl
            message = OmniChannelMessage(
                tenant_id=payload["tenant_id"],
                channel_id=payload["channel_id"],
                channel_type=channel_type,
                conversation_id=conversation.id,
                external_user_id=payload["external_user_id"],
                external_message_id=payload["external_message_id"],
                direction=payload["direction"],
                source=payload["source"],
                content=payload["content"],
                attachments=payload["attachments"],
                message_metadata=metadata,
            )
            message.created_at = created_at
            session.add(message)
            session.commit()
            session.refresh(message)
            conv_row_id = str(message.conversation_id)
            msg_row_id = str(message.id)
        publish_omnichannel_change(
            tenant_id=payload["tenant_id"],
            channel_id=payload["channel_id"],
            conversation_id=conv_row_id,
            message_id=msg_row_id,
            kind="messages",
        )
        from services.omnichannel.mini_crm_service import MiniCrmService

        MiniCrmService.ensure_lead_for_conversation(
            tenant_id=payload["tenant_id"],
            conversation_id=conv_row_id,
        )
        return {
            "id": msg_row_id,
            "conversation_id": conv_row_id,
            "channel_type": channel_type.value,
        }

    @classmethod
    def create_sync_job(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        created_by: str,
        since: datetime | None,
        until: datetime | None,
    ) -> dict[str, Any]:
        since = cls._normalize_dt(since)
        until = cls._normalize_dt(until)
        with Session(db.engine, expire_on_commit=False) as session:
            channel_type = cls._get_channel_type(session, tenant_id, channel_id)
            row = OmniChannelSyncJob(
                tenant_id=tenant_id,
                channel_id=channel_id,
                channel_type=channel_type,
                since_at=since,
                until_at=until,
                status=OmniChannelSyncJobStatus.PENDING,
                progress=0,
                total_messages=0,
                synced_messages=0,
                created_by=created_by,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return cls._sync_job_to_dict(row)

    @staticmethod
    def _sync_job_to_dict(row: OmniChannelSyncJob) -> dict[str, Any]:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "channel_id": row.channel_id,
            "channel_type": row.channel_type.value,
            "status": row.status.value,
            "progress": row.progress,
            "total_messages": row.total_messages,
            "synced_messages": row.synced_messages,
            "last_error": row.last_error,
            "since_at": row.since_at,
            "until_at": row.until_at,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def get_sync_job(cls, *, tenant_id: str, channel_id: str, job_id: str) -> dict[str, Any] | None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelSyncJob).where(
                    OmniChannelSyncJob.id == job_id,
                    OmniChannelSyncJob.tenant_id == tenant_id,
                    OmniChannelSyncJob.channel_id == channel_id,
                )
            )
            if not row:
                return None
            return cls._sync_job_to_dict(row)

    @classmethod
    def run_sync_job(cls, *, tenant_id: str, channel_id: str, job_id: str) -> None:
        with Session(db.engine, expire_on_commit=False) as session:
            row = session.scalar(
                select(OmniChannelSyncJob).where(
                    OmniChannelSyncJob.id == job_id,
                    OmniChannelSyncJob.tenant_id == tenant_id,
                    OmniChannelSyncJob.channel_id == channel_id,
                )
            )
            if not row:
                return
            row.status = OmniChannelSyncJobStatus.RUNNING
            row.started_at = datetime.utcnow()
            session.commit()

            try:
                config = session.scalar(
                    select(OmniChannelConfig).where(
                        OmniChannelConfig.tenant_id == tenant_id,
                        OmniChannelConfig.channel_id == channel_id,
                    )
                )
                if not config:
                    raise ValueError("Channel not found")
                if not config.enabled:
                    raise ValueError("Channel is disabled")

                if config.channel_type not in (OmniChannelType.FACEBOOK_MESSENGER, OmniChannelType.INSTAGRAM_DM):
                    raise ValueError(f"Sync history is not implemented for channel type: {config.channel_type.value}")

                # Full-window sync (no since/until): refresh PSID display name + profile photo from User Profile API
                # so the conversation list and UI fallbacks match Meta before pulling conversation history.
                if (
                    config.channel_type == OmniChannelType.FACEBOOK_MESSENGER
                    and row.since_at is None
                    and row.until_at is None
                ):
                    cls._refresh_all_messenger_participant_profiles(
                        session=session,
                        tenant_id=tenant_id,
                        channel_id=channel_id,
                    )

                synced_messages, discovered_messages = cls._sync_meta_history(
                    session=session,
                    config=config,
                    since_at=row.since_at,
                    until_at=row.until_at,
                    max_messages=cls._MAX_SYNC_MESSAGES,
                )

                row.total_messages = discovered_messages
                row.synced_messages = synced_messages
                row.progress = 100
                row.status = OmniChannelSyncJobStatus.SUCCEEDED
                row.last_error = None
            except Exception as e:
                logger.exception("Omnichannel sync failed channel_id=%s job_id=%s", channel_id, job_id)
                row.status = OmniChannelSyncJobStatus.FAILED
                row.last_error = str(e)
                row.progress = 0
            finally:
                row.finished_at = datetime.utcnow()
                session.commit()

    @staticmethod
    def _parse_meta_time(value: str | None) -> datetime | None:
        if not value:
            return None
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _is_within_time_range(created_at: datetime, since_at: datetime | None, until_at: datetime | None) -> bool:
        if since_at and created_at < since_at:
            return False
        if until_at and created_at > until_at:
            return False
        return True

    @staticmethod
    def _upsert_sync_message(
        *,
        session: Session,
        tenant_id: str,
        channel_id: str,
        external_message_id: str,
        external_user_id: str,
        direction: OmniChannelMessageDirection,
        content: str,
        created_at: datetime,
        metadata: dict[str, Any],
        conversation_hint_name: str | None = None,
        conversation_hint_pic: str | None = None,
    ) -> bool:
        existed = session.scalar(
            select(OmniChannelMessage.id).where(
                OmniChannelMessage.tenant_id == tenant_id,
                OmniChannelMessage.channel_id == channel_id,
                OmniChannelMessage.external_message_id == external_message_id,
            )
        )
        if existed:
            return False

        channel_type = session.scalar(
            select(OmniChannelConfig.channel_type).where(
                OmniChannelConfig.tenant_id == tenant_id,
                OmniChannelConfig.channel_id == channel_id,
            )
        )
        if not channel_type:
            raise ValueError("Channel not found")

        conversation = session.scalar(
            select(OmniChannelConversation).where(
                OmniChannelConversation.tenant_id == tenant_id,
                OmniChannelConversation.channel_id == channel_id,
                OmniChannelConversation.external_user_id == external_user_id,
            )
        )
        if conversation:
            if not conversation.last_message_at or conversation.last_message_at < created_at:
                conversation.last_message_at = created_at
            hint_n = (conversation_hint_name or "").strip()
            hint_p = (conversation_hint_pic or "").strip()
            if hint_n and not (conversation.participant_display_name or "").strip():
                conversation.participant_display_name = hint_n
            if hint_p and not (conversation.participant_profile_pic_url or "").strip():
                conversation.participant_profile_pic_url = hint_p
        else:
            conversation = OmniChannelConversation(
                tenant_id=tenant_id,
                channel_id=channel_id,
                channel_type=channel_type,
                external_user_id=external_user_id,
                last_message_at=created_at,
                participant_display_name=(conversation_hint_name or "").strip() or None,
                participant_profile_pic_url=(conversation_hint_pic or "").strip() or None,
            )
            session.add(conversation)
            session.flush()

        message = OmniChannelMessage(
            tenant_id=tenant_id,
            channel_id=channel_id,
            channel_type=channel_type,
            conversation_id=conversation.id,
            external_user_id=external_user_id,
            external_message_id=external_message_id,
            direction=direction,
            source=OmniChannelMessageSource.SYNC,
            content=content,
            attachments=[],
            message_metadata=metadata,
        )
        message.created_at = created_at
        session.add(message)
        session.flush()
        return True

    @classmethod
    def _refresh_all_messenger_participant_profiles(
        cls,
        *,
        session: Session,
        tenant_id: str,
        channel_id: str,
    ) -> None:
        """Re-resolve every PSID row from Graph (name + profile picture) for this Messenger channel."""
        messenger_cfg = ChannelConfigService.get_messenger_channel_config(channel_id)
        if not messenger_cfg or messenger_cfg["tenant_id"] != tenant_id:
            logger.warning(
                "Skip messenger participant bulk refresh: missing or mismatched config tenant_id=%s channel_id=%s",
                tenant_id,
                channel_id,
            )
            return
        convs = list(
            session.scalars(
                select(OmniChannelConversation).where(
                    OmniChannelConversation.tenant_id == tenant_id,
                    OmniChannelConversation.channel_id == channel_id,
                )
            ).all()
        )
        for conv in convs:
            prof = fetch_messenger_user_profile(
                psid=conv.external_user_id,
                access_token=messenger_cfg["page_access_token"],
                graph_version=messenger_cfg["graph_api_version"],
            )
            pname = str(prof.get("name") or "").strip()
            purl = str(prof.get("profile_pic") or "").strip()
            if pname:
                conv.participant_display_name = pname
            if purl:
                conv.participant_profile_pic_url = purl
        session.commit()
        publish_omnichannel_change(
            tenant_id=tenant_id,
            channel_id=channel_id,
            kind="conversations",
        )

    @classmethod
    def _sync_meta_history(
        cls,
        *,
        session: Session,
        config: OmniChannelConfig,
        since_at: datetime | None,
        until_at: datetime | None,
        max_messages: int,
    ) -> tuple[int, int]:
        page_access_token = config.decrypt_page_access_token()
        api_version = config.graph_api_version or "v23.0"
        page_id = config.page_id
        platform = "instagram" if config.channel_type == OmniChannelType.INSTAGRAM_DM else "messenger"

        base_url = f"https://graph.facebook.com/{api_version}"
        conversations_url = f"{base_url}/{page_id}/conversations"
        conversations_params: dict[str, Any] = {
            "platform": platform,
            "fields": "id,updated_time,participants.limit(10){id,name,picture}",
            "limit": 25,
            "access_token": page_access_token,
        }

        discovered_messages = 0
        synced_messages = 0
        next_conversations_url: str | None = conversations_url
        next_conversations_params: dict[str, Any] | None = conversations_params

        while next_conversations_url and discovered_messages < max_messages:
            response = ssrf_proxy.get(next_conversations_url, params=next_conversations_params)
            response.raise_for_status()
            payload = response.json()
            conversations = payload.get("data") or []
            for conversation in conversations:
                conversation_id = str(conversation.get("id") or "").strip()
                if not conversation_id:
                    continue

                participants = (conversation.get("participants") or {}).get("data") or []
                participant_ids = [str(item.get("id") or "").strip() for item in participants if item.get("id")]
                customer_display_name = ""
                customer_pic_url = ""
                for p in participants:
                    if not isinstance(p, dict):
                        continue
                    pid = str(p.get("id") or "").strip()
                    if pid and pid != page_id:
                        customer_display_name = str(p.get("name") or "").strip()
                        customer_pic_url = extract_graph_picture_url(p.get("picture"))
                        break

                messages_url = f"{base_url}/{conversation_id}/messages"
                messages_params: dict[str, Any] = {
                    "fields": "id,message,from{id,name,picture},created_time",
                    "limit": cls._GRAPH_PAGE_LIMIT,
                    "access_token": page_access_token,
                }
                next_messages_url: str | None = messages_url
                next_messages_params: dict[str, Any] | None = messages_params

                while next_messages_url and discovered_messages < max_messages:
                    message_response = ssrf_proxy.get(next_messages_url, params=next_messages_params)
                    message_response.raise_for_status()
                    message_payload = message_response.json()
                    messages = message_payload.get("data") or []

                    for message in messages:
                        message_id = str(message.get("id") or "").strip()
                        if not message_id:
                            continue

                        created_at = cls._parse_meta_time(str(message.get("created_time") or ""))
                        if not created_at:
                            continue
                        if not cls._is_within_time_range(created_at, since_at, until_at):
                            continue

                        discovered_messages += 1
                        from_obj = message.get("from") or {}
                        from_id = str(from_obj.get("id") or "").strip() if isinstance(from_obj, dict) else ""
                        from_name = str(from_obj.get("name") or "").strip() if isinstance(from_obj, dict) else ""
                        from_pic = extract_graph_picture_url(from_obj.get("picture")) if isinstance(from_obj, dict) else ""

                        direction = (
                            OmniChannelMessageDirection.OUTBOUND if from_id and from_id == page_id else OmniChannelMessageDirection.INBOUND
                        )
                        external_user_id = ""
                        if direction == OmniChannelMessageDirection.INBOUND and from_id:
                            external_user_id = from_id
                        else:
                            external_user_id = next(
                                (item for item in participant_ids if item and item != page_id),
                                from_id or page_id,
                            )
                        if not external_user_id:
                            continue

                        msg_meta: dict[str, Any] = {"conversation_id": conversation_id, "graph_sync": True}
                        if direction == OmniChannelMessageDirection.INBOUND:
                            if from_name:
                                msg_meta["sender_display_name"] = from_name
                            if from_pic:
                                msg_meta["sender_profile_pic_url"] = from_pic
                        else:
                            if from_name:
                                msg_meta["channel_actor_name"] = from_name
                            if from_pic:
                                msg_meta["channel_actor_picture_url"] = from_pic

                        inserted = cls._upsert_sync_message(
                            session=session,
                            tenant_id=config.tenant_id,
                            channel_id=config.channel_id,
                            external_message_id=message_id,
                            external_user_id=external_user_id,
                            direction=direction,
                            content=str(message.get("message") or ""),
                            created_at=created_at,
                            metadata=msg_meta,
                            conversation_hint_name=customer_display_name or None,
                            conversation_hint_pic=customer_pic_url or None,
                        )
                        if inserted:
                            synced_messages += 1

                    paging_next = ((message_payload.get("paging") or {}).get("next") or "").strip()
                    next_messages_url = paging_next or None
                    next_messages_params = None if paging_next else None

            paging_next_conversations = ((payload.get("paging") or {}).get("next") or "").strip()
            next_conversations_url = paging_next_conversations or None
            next_conversations_params = None if paging_next_conversations else None

        session.commit()
        publish_omnichannel_change(
            tenant_id=config.tenant_id,
            channel_id=config.channel_id,
            kind="history_sync",
        )
        return synced_messages, discovered_messages

    @classmethod
    def get_channel_stats(
        cls,
        *,
        tenant_id: str,
        channel_id: str,
        since: datetime | None,
        until: datetime | None,
    ) -> dict[str, Any]:
        since = cls._normalize_dt(since)
        until = cls._normalize_dt(until)
        conditions: list[Any] = [OmniChannelMessage.tenant_id == tenant_id, OmniChannelMessage.channel_id == channel_id]
        if since is not None:
            conditions.append(OmniChannelMessage.created_at >= since)
        if until is not None:
            conditions.append(OmniChannelMessage.created_at <= until)
        where_clause = and_(*conditions)

        with Session(db.engine, expire_on_commit=False) as session:
            total_messages = session.scalar(select(func.count()).select_from(OmniChannelMessage).where(where_clause)) or 0
            inbound_count = (
                session.scalar(
                    select(func.count()).select_from(OmniChannelMessage).where(
                        where_clause, OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND
                    )
                )
                or 0
            )
            outbound_count = (
                session.scalar(
                    select(func.count()).select_from(OmniChannelMessage).where(
                        where_clause, OmniChannelMessage.direction == OmniChannelMessageDirection.OUTBOUND
                    )
                )
                or 0
            )
            active_conversations = (
                session.scalar(
                    select(func.count()).select_from(OmniChannelConversation).where(
                        OmniChannelConversation.tenant_id == tenant_id,
                        OmniChannelConversation.channel_id == channel_id,
                    )
                )
                or 0
            )
        return {
            "total_messages": total_messages,
            "inbound_messages": inbound_count,
            "outbound_messages": outbound_count,
            "active_conversations": active_conversations,
        }

    @classmethod
    def get_health(cls, *, tenant_id: str, channel_id: str) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
            if not config:
                raise ValueError("Channel not found")

            latest_inbound = session.scalar(
                select(OmniChannelMessage.created_at)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.channel_id == channel_id,
                    OmniChannelMessage.direction == OmniChannelMessageDirection.INBOUND,
                )
                .order_by(OmniChannelMessage.created_at.desc())
                .limit(1)
            )
            latest_outbound = session.scalar(
                select(OmniChannelMessage.created_at)
                .where(
                    OmniChannelMessage.tenant_id == tenant_id,
                    OmniChannelMessage.channel_id == channel_id,
                    OmniChannelMessage.direction == OmniChannelMessageDirection.OUTBOUND,
                )
                .order_by(OmniChannelMessage.created_at.desc())
                .limit(1)
            )
            return {
                "channel_id": config.channel_id,
                "enabled": config.enabled,
                "channel_type": config.channel_type.value,
                "last_inbound_at": latest_inbound,
                "last_outbound_at": latest_outbound,
                "webhook_path": f"/triggers/{cls._CHANNEL_TO_WEBHOOK_PROVIDER.get(config.channel_type, 'messenger')}/webhook/{config.channel_id}",
            }

    @staticmethod
    def test_webhook(*, tenant_id: str, channel_id: str) -> dict[str, Any]:
        with Session(db.engine, expire_on_commit=False) as session:
            config = session.scalar(
                select(OmniChannelConfig).where(
                    OmniChannelConfig.tenant_id == tenant_id,
                    OmniChannelConfig.channel_id == channel_id,
                )
            )
            if not config:
                raise ValueError("Channel not found")
            # Smoke test only: configuration exists and channel is enabled.
            return {
                "success": bool(config.enabled),
                "channel_id": config.channel_id,
                "channel_type": config.channel_type.value,
                "message": "Webhook route is configured.",
            }

    @staticmethod
    def bulk_record_messages(payloads: Iterable[MessageWritePayload]) -> None:
        for payload in payloads:
            OmnichannelOpsService.record_message(payload)
