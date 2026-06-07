"""Auto request_user_info card for new OA users (ported from zca-bridge requestInfoSender.ts + infoRequestTracker)."""

from __future__ import annotations

import logging
from typing import TypedDict

from extensions.ext_redis import redis_client
from services.omnichannel.zalo_oa_sender import ZaloOaSender

logger = logging.getLogger(__name__)

_DEFAULT_TITLE = "Xin chào!"
_DEFAULT_SUBTITLE = "Vui lòng chia sẻ thông tin để chúng tôi hỗ trợ bạn tốt hơn."
_DEFAULT_IMAGE = "https://stc-zaloprofile.zdn.vn/pc/v1/images/logo_zalo.png"


class ZaloInfoCardConfig(TypedDict):
    enabled: bool
    title: str
    subtitle: str
    image_url: str


class ZaloOaInfoCardService:
    @staticmethod
    def _redis_key(channel_id: str, user_id: str) -> str:
        return f"zalo:info_card_sent:{channel_id}:{user_id}"

    @staticmethod
    def resolve_config(channel_config: dict) -> ZaloInfoCardConfig:
        return {
            "enabled": bool(channel_config.get("zalo_info_card_enabled")),
            "title": (channel_config.get("zalo_info_card_title") or _DEFAULT_TITLE).strip() or _DEFAULT_TITLE,
            "subtitle": (
                (channel_config.get("zalo_info_card_subtitle") or _DEFAULT_SUBTITLE).strip() or _DEFAULT_SUBTITLE
            ),
            "image_url": (channel_config.get("zalo_info_card_image_url") or _DEFAULT_IMAGE).strip() or _DEFAULT_IMAGE,
        }

    @classmethod
    def maybe_send_on_first_inbound(
        cls,
        *,
        channel_id: str,
        user_id: str,
        channel_config: dict,
    ) -> None:
        card = cls.resolve_config(channel_config)
        if not card["enabled"]:
            return
        key = cls._redis_key(channel_id, user_id)
        if redis_client.get(key):
            return
        token = (channel_config.get("oa_access_token") or "").strip()
        if not token:
            return
        result = ZaloOaSender(token).send_request_user_info(
            user_id,
            title=card["title"],
            subtitle=card["subtitle"],
            image_url=card["image_url"],
        )
        if result.get("ok"):
            redis_client.set(key, "1")
