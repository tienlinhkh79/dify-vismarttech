"""Provider adapter contracts for omnichannel runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ChannelProvider(ABC):
    """Provider-level contract for webhook channels."""

    provider: str
    channel_type: str

    @abstractmethod
    def verify_handshake(self, request_args: dict[str, Any], channel_config: dict[str, Any]) -> str:
        """Verify provider webhook handshake and return challenge."""

    @abstractmethod
    def verify_signature(self, signature_header: str | None, payload: bytes, channel_config: dict[str, Any]) -> bool:
        """Verify request signature."""

    @abstractmethod
    def parse_events(self, channel_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize provider payload to channel-agnostic events."""

