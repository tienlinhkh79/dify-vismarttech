"""Redis pub/sub notifications for omnichannel console UI (SSE subscribers)."""

from __future__ import annotations

import json
import logging

from extensions.ext_redis import get_pubsub_broadcast_channel

logger = logging.getLogger(__name__)


def omnichannel_pubsub_topic(*, tenant_id: str, channel_id: str) -> str:
    """Logical Redis topic for one workspace channel (must match SSE subscription)."""
    return f"omnichannel:v1:{tenant_id}:{channel_id}"


def publish_omnichannel_change(
    *,
    tenant_id: str,
    channel_id: str,
    conversation_id: str | None = None,
    message_id: str | None = None,
    kind: str = "messages",
) -> None:
    """Notify console clients that omnichannel data changed (webhook, sync, or profile refresh)."""
    payload = json.dumps(
        {
            "type": "omnichannel",
            "kind": kind,
            "channel_id": channel_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    topic = omnichannel_pubsub_topic(tenant_id=tenant_id, channel_id=channel_id)
    try:
        get_pubsub_broadcast_channel().topic(topic).publish(payload)
    except Exception:
        logger.warning(
            "Omnichannel realtime publish failed tenant_id=%s channel_id=%s",
            tenant_id,
            channel_id,
            exc_info=True,
        )
