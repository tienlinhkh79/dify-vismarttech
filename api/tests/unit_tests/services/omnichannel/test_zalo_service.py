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


def test_verify_event_signature_mini_app_sorted_values_style() -> None:
    """Zalo Open API doc: sha256(concat(sorted values) + api_key)."""
    secret = "api_key"
    payload = {"zebra": "z", "alpha": "a", "nested": {"k": 1}}
    content = "a" + json.dumps({"k": 1}, separators=(",", ":"), sort_keys=True) + "z"
    mac = hashlib.sha256(f"{content}{secret}".encode()).hexdigest()
    body = json.dumps(payload, separators=(",", ":"))
    assert ZaloService.verify_event_signature(mac, body.encode("utf-8"), secret, payload) is True


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


def test_parse_message_events_ignores_oa_originated_events() -> None:
    """OA-outbound samples must not enter the signed message path (avoids false 401 on webhook URL check)."""
    payload = {
        "event_name": "oa_send_text",
        "sender": {"id": "123"},
        "message": {"text": "hello"},
    }
    assert ZaloService.parse_message_events("ch", payload) == []


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


def test_parse_message_events_accepts_legacy_unnamed_payload_with_text() -> None:
    payload = {"sender": {"id": "u2"}, "message": {"text": "legacy"}}
    events = ZaloService.parse_message_events("ch", payload)
    assert len(events) == 1
    assert events[0]["text"] == "legacy"


def test_verify_event_signature_body_only_oa_id_mac_uses_fallback_app_id() -> None:
    """URL-check POST may include oa_id but sign with application app_id (stored on channel)."""
    secret = "k"
    body = '{"oa_id":"111","timestamp":"5"}'
    payload = json.loads(body)
    mac = hashlib.sha256(f"999{body}5{secret}".encode()).hexdigest()
    assert (
        ZaloService.verify_event_signature(
            mac,
            body.encode("utf-8"),
            secret,
            payload,
            fallback_app_id="999",
            fallback_oa_id="111",
        )
        is True
    )
