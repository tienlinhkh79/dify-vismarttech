from services.omnichannel.messenger_service import OmniChannelIncomingEvent
from services.omnichannel.omnichannel_app_start_input_keys import OmnichannelAppStartInputKey
from services.omnichannel.omnichannel_workflow_inputs import build_event_query, build_workflow_start_inputs


class TestOmnichannelWorkflowInputs:
    def test_build_event_query_prefers_button_payload(self) -> None:
        event: OmniChannelIncomingEvent = {
            "channel": "facebook_messenger",
            "channel_id": "ch-1",
            "external_account_id": "page-1",
            "external_user_id": "user-1",
            "text": "Giày nam",
            "interaction_type": "postback",
            "button_payload": "giay_nam",
            "button_title": "Giày nam",
            "raw_event": {},
        }
        assert build_event_query(event) == "Giày nam (giay_nam)"

    def test_build_event_query_uses_plain_text_without_button(self) -> None:
        event: OmniChannelIncomingEvent = {
            "channel": "facebook_messenger",
            "channel_id": "ch-1",
            "external_account_id": "page-1",
            "external_user_id": "user-1",
            "text": "xin chào",
            "raw_event": {},
        }
        assert build_event_query(event) == "xin chào"

    def test_build_workflow_start_inputs_includes_button_metadata(self) -> None:
        event: OmniChannelIncomingEvent = {
            "channel": "zalo_oa",
            "channel_id": "ch-1",
            "external_account_id": "oa-1",
            "external_user_id": "user-1",
            "text": "search_more",
            "interaction_type": "button_click",
            "button_payload": "search_more",
            "button_title": "Xem thêm",
            "raw_event": {},
        }
        inputs = build_workflow_start_inputs(
            channel_id="ch-1",
            channel_type="zalo_oa",
            conversation_id="conv-1",
            external_user_id="user-1",
            event=event,
        )
        assert inputs[OmnichannelAppStartInputKey.INTERACTION_TYPE] == "button_click"
        assert inputs[OmnichannelAppStartInputKey.BUTTON_PAYLOAD] == "search_more"
        assert inputs[OmnichannelAppStartInputKey.BUTTON_TITLE] == "Xem thêm"
