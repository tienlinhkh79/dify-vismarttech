from unittest.mock import patch

from services.omnichannel.zalo_personal_presence_service import ZaloPersonalPresenceService


class TestZaloPersonalPresenceService:
    def test_inbound_metadata_wraps_message_meta(self) -> None:
        meta = {"msgId": "1", "cliMsgId": "2", "uidFrom": "u1"}
        result = ZaloPersonalPresenceService.inbound_metadata(meta)
        assert result["zalo_message_meta"] == meta

    def test_extract_message_meta_round_trip(self) -> None:
        meta = {"msgId": "9"}
        wrapped = ZaloPersonalPresenceService.inbound_metadata(meta)
        assert ZaloPersonalPresenceService.extract_message_meta(wrapped) == meta

    @patch("services.omnichannel.zalo_personal_presence_service.ZaloPersonalSessionService.mark_seen")
    @patch("services.omnichannel.zalo_personal_presence_service.ZaloPersonalSessionService.send_typing")
    @patch.object(ZaloPersonalPresenceService, "simulate_human_typing_delay")
    def test_prepare_before_send_runs_seen_typing_delay(
        self,
        mock_delay,
        mock_typing,
        mock_seen,
    ) -> None:
        meta = {"msgId": "1"}
        ZaloPersonalPresenceService.prepare_before_send(
            channel_id="ch-1",
            thread_id="thread-1",
            reply_text="Xin chào",
            message_meta=meta,
        )
        mock_seen.assert_called_once()
        mock_typing.assert_called_once_with(channel_id="ch-1", thread_id="thread-1")
        mock_delay.assert_called_once_with("Xin chào")

    @patch("services.omnichannel.zalo_personal_presence_service.ZaloPersonalSessionService.mark_seen")
    @patch("services.omnichannel.zalo_personal_presence_service.ZaloPersonalSessionService.send_typing")
    @patch.object(ZaloPersonalPresenceService, "simulate_human_typing_delay")
    def test_prepare_before_send_respects_skip_flags(
        self,
        mock_delay,
        mock_typing,
        mock_seen,
    ) -> None:
        ZaloPersonalPresenceService.prepare_before_send(
            channel_id="ch-1",
            thread_id="thread-1",
            reply_text="Hi",
            message_meta={"msgId": "1"},
            options={"skip_seen": True, "skip_typing": True, "skip_delay": True},
        )
        mock_seen.assert_not_called()
        mock_typing.assert_not_called()
        mock_delay.assert_not_called()
