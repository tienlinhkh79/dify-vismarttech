import json
import time
from unittest.mock import MagicMock, patch

from services.omnichannel.omnichannel_auto_reply_debounce_service import OmnichannelAutoReplyDebounceService


class TestOmnichannelAutoReplyDebounceService:
    @patch("tasks.omnichannel_tasks.process_debounced_auto_reply")
    @patch("services.omnichannel.omnichannel_auto_reply_debounce_service.redis_client")
    def test_enqueue_buffers_fragment_and_schedules_task(self, mock_redis: MagicMock, mock_task: MagicMock) -> None:
        pipe = MagicMock()
        pipe.rpush.return_value = pipe
        pipe.set.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute.return_value = [1, True, True]
        mock_redis.pipeline.return_value = pipe

        ok = OmnichannelAutoReplyDebounceService.enqueue(
            channel_type="facebook_messenger",
            channel_id="ch-1",
            tenant_id="tenant-1",
            external_user_id="user-1",
            fragment={
                "text": "hello",
                "conversation_id": "conv-1",
                "event": {"text": "hello"},
            },
        )

        assert ok is True
        mock_task.apply_async.assert_called_once()
        args, kwargs = mock_task.apply_async.call_args
        assert args[0] == ["ch-1", "user-1"]
        assert kwargs["countdown"] == 4

    def test_merge_texts_joins_non_empty_parts(self) -> None:
        merged = OmnichannelAutoReplyDebounceService.merge_texts(
            [
                {"text": "xin chào"},
                {"text": "cho mình hỏi"},
                {"text": ""},
                {"text": "menu phở"},
            ]
        )
        assert merged == "xin chào\ncho mình hỏi\nmenu phở"

    @patch("services.omnichannel.omnichannel_auto_reply_executor.OmnichannelAutoReplyExecutor.execute_merged")
    @patch("tasks.omnichannel_tasks.process_debounced_auto_reply")
    @patch("services.omnichannel.omnichannel_auto_reply_debounce_service.redis_client")
    def test_process_reschedules_when_user_still_typing(
        self,
        mock_redis: MagicMock,
        mock_task: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        mock_redis.get.return_value = str(time.time()).encode()
        status = OmnichannelAutoReplyDebounceService.process(channel_id="ch-1", external_user_id="user-1")
        assert status == "rescheduled"
        mock_task.apply_async.assert_called_once()
        mock_execute.assert_not_called()

    @patch("services.omnichannel.omnichannel_auto_reply_executor.OmnichannelAutoReplyExecutor.execute_merged")
    @patch("services.omnichannel.omnichannel_auto_reply_debounce_service.redis_client")
    def test_process_drains_and_executes_after_silence(
        self,
        mock_redis: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        mock_redis.get.return_value = str(time.time() - 10).encode()
        fragment = json.dumps(
            {
                "channel_type": "facebook_messenger",
                "tenant_id": "tenant-1",
                "text": "hello",
                "conversation_id": "conv-1",
                "event": {"text": "hello"},
            }
        )
        mock_redis.lrange.return_value = [fragment.encode()]

        status = OmnichannelAutoReplyDebounceService.process(channel_id="ch-1", external_user_id="user-1")

        assert status == "processed"
        mock_redis.delete.assert_called_once()
        mock_execute.assert_called_once()
