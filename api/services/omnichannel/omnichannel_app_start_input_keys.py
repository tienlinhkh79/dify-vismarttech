"""Canonical ``inputs`` keys passed to AppGenerateService for omnichannel-driven replies.

These string values are part of the workflow author contract; add new keys here only
with a clear versioning or naming scheme (e.g. ``omnichannel_*`` namespace).
"""

from __future__ import annotations


class OmnichannelAppStartInputKey:
    """Stable variable names for chat / agent / advanced-chat app ``inputs``."""

    CHANNEL_ID = "omnichannel_channel_id"
    CHANNEL_TYPE = "omnichannel_channel_type"
    CONVERSATION_ID = "omnichannel_conversation_id"
    EXTERNAL_USER_ID = "omnichannel_external_user_id"
