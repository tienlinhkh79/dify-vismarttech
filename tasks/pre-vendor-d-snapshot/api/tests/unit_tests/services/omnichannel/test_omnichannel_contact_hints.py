"""Tests for omnichannel contact hint extraction."""

from services.omnichannel.omnichannel_contact_hints import (
    extract_display_name_from_text,
    looks_like_anonymous_display,
)


def test_extract_display_name_from_name_line() -> None:
    assert extract_display_name_from_text("Name : Node Lee\nPhone: 0338472701") == "Node Lee"


def test_extract_display_name_vietnamese_label() -> None:
    assert extract_display_name_from_text("Họ tên: Lê Đức Nam") == "Lê Đức Nam"


def test_looks_like_anonymous_display_for_uuid() -> None:
    assert looks_like_anonymous_display(
        "84831b87-4de5-45af-9d12-ff26b05cf48b",
        external_user_id="84831b87-4de5-45af-9d12-ff26b05cf48b",
    )


def test_looks_like_anonymous_display_for_real_name() -> None:
    assert not looks_like_anonymous_display("Node Lee", external_user_id="84831b87-4de5-45af-9d12-ff26b05cf48b")
