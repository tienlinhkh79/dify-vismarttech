"""Tests for Zalo OA webhook helpers."""

from __future__ import annotations

import hashlib
import json

from services.omnichannel.zalo_service import ZaloService


def test_verify_event_signature_documented_mac() -> None:
    secret = "oa_secret_key"
    body = '{"app_id":"123","timestamp":"999","event_name":"oa_send_text"}'
    payload = {"app_id": "123", "timestamp": "999", "event_name": "oa_send_text"}
    mac = hashlib.sha256(f"123{body}999{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_accepts_time_stamp_camel_case() -> None:
    secret = "oa_secret_key"
    body = '{"app_id":"123","timeStamp":"888"}'
    payload = {"app_id": "123", "timeStamp": "888"}
    mac = hashlib.sha256(f"123{body}888{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_accepts_app_id_alias() -> None:
    secret = "oa_secret_key"
    body = '{"appId":"456","timestamp":"1"}'
    payload = {"appId": "456", "timestamp": "1"}
    mac = hashlib.sha256(f"456{body}1{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_accepts_v1_prefix_header() -> None:
    secret = "s"
    body = '{"app_id":"1","timestamp":"2"}'
    payload = {"app_id": "1", "timestamp": "2"}
    mac = hashlib.sha256(f"1{body}2{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(f"v1={mac}", body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_uppercase_hex_header() -> None:
    secret = "s"
    body = '{"app_id":"1","timestamp":"2"}'
    payload = {"app_id": "1", "timestamp": "2"}
    mac = hashlib.sha256(f"1{body}2{secret}".encode()).hexdigest().upper()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_missing_header_skips_check() -> None:
    assert ZaloService.verify_event_signature(None, b"{}", "secret", {}) is True


def test_verify_event_signature_wrong_mac() -> None:
    secret = "oa_secret_key"
    body = '{"app_id":"123","timestamp":"999"}'
    payload = {"app_id": "123", "timestamp": "999"}
    assert ZaloService.verify_event_signature("deadbeef", body.encode("utf-8"), secret, payload) is False


def test_verify_event_signature_fallback_app_id_when_body_omits_it() -> None:
    secret = "oa_secret_key"
    body = '{"timestamp":"777","event_name":"ping"}'
    payload = {"timestamp": "777", "event_name": "ping"}
    mac = hashlib.sha256(f"999{body}777{secret}".encode()).hexdigest()
    assert (
        ZaloService.verify_event_signature(
            mac,
            body.encode("utf-8"),
            secret,
            payload,
            fallback_app_id="999",
        )
        is True
    )


def test_verify_event_signature_timestamp_from_header() -> None:
    secret = "oa_secret_key"
    body = '{"app_id":"1","event_name":"ping"}'
    payload = {"app_id": "1", "event_name": "ping"}
    mac = hashlib.sha256(f"1{body}555{secret}".encode()).hexdigest()
    assert (
        ZaloService.verify_event_signature(
            mac,
            body.encode("utf-8"),
            secret,
            payload,
            header_timestamp="555",
        )
        is True
    )


def test_verify_event_signature_accepts_mac_prefix_with_space() -> None:
    secret = "s"
    body = '{"app_id":"1","timestamp":"2"}'
    payload = {"app_id": "1", "timestamp": "2"}
    mac = hashlib.sha256(f"1{body}2{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(f"mac = {mac}", body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_inner_data_field_as_mac_segment() -> None:
    secret = "oa_secret_key"
    inner = '{"msg":"hi"}'
    payload = {"app_id": "1", "timestamp": "9", "data": json.loads(inner)}
    body = json.dumps(payload, separators=(",", ":"))
    mac = hashlib.sha256(f"1{inner}9{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_verify_event_signature_accepts_appid_lower_key() -> None:
    secret = "s"
    body = '{"appid":42,"timestamp":"3"}'
    payload = {"appid": 42, "timestamp": "3"}
    mac = hashlib.sha256(f"42{body}3{secret}".encode()).hexdigest()
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


def test_parse_message_events_accepts_oa_self_send_as_outbound() -> None:
    payload = {
        "event_name": "oa_send_text",
        "sender": {"id": "oa1"},
        "recipient": {"id": "u1"},
        "message": {"text": "hello", "msg_id": "m1"},
    }
    events = ZaloService.parse_message_events("ch", payload)
    assert len(events) == 1
    assert events[0]["external_user_id"] == "u1"
    assert events[0].get("is_self") is True
    assert events[0]["text"] == "hello"


def test_parse_message_events_accepts_user_send_text() -> None:
    payload = {
        "event_name": "user_send_text",
        "sender": {"id": "u1"},
        "message": {"text": "hi"},
        "oa_id": "oa9",
    }
    events = ZaloService.parse_message_events("ch", payload)
    assert len(events) == 1
    assert events[0]["external_user_id"] == "u1"
    assert events[0]["text"] == "hi"


def test_parse_message_events_accepts_user_send_image_with_attachment() -> None:
    payload = {
        "event_name": "user_send_image",
        "sender": {"id": "u1"},
        "message": {
            "text": "",
            "msg_id": "m2",
            "attachments": [{"type": "image", "payload": {"url": "https://cdn.example/a.jpg"}}],
        },
    }
    events = ZaloService.parse_message_events("ch", payload)
    assert len(events) == 1
    assert events[0]["attachments"][0]["url"] == "https://cdn.example/a.jpg"


def test_parse_message_events_ignores_follow_events() -> None:
    payload = {"event_name": "follow", "sender": {"id": "u1"}}
    assert ZaloService.parse_message_events("ch", payload) == []
