import pytest

from services.omnichannel.meta_cdn import (
    is_meta_cdn_url,
    sanitize_attachment_list,
    sanitize_browser_image_url,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://scontent.fsgn8-1.fna.fbcdn.net/v/t39.30808-1/x.png", True),
        ("https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=1", True),
        ("https://cdn.zalo.me/avatar.jpg", False),
        ("", False),
        (None, False),
    ],
)
def test_is_meta_cdn_url(url: str | None, expected: bool) -> None:
    assert is_meta_cdn_url(url) is expected


def test_sanitize_browser_image_url_strips_meta() -> None:
    assert sanitize_browser_image_url("https://scontent.fsgn8-1.fna.fbcdn.net/v/t1/x.png") is None
    assert sanitize_browser_image_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"


def test_sanitize_attachment_list_blocks_meta_urls() -> None:
    result = sanitize_attachment_list(
        [
            {"url": "https://scontent.fsgn8-1.fna.fbcdn.net/v/t1/x.png", "type": "image"},
            {"url": "https://cdn.example.com/ok.jpg", "type": "image"},
        ]
    )
    assert result[0]["url"] is None
    assert result[0]["meta_cdn_blocked"] is True
    assert result[1]["url"] == "https://cdn.example.com/ok.jpg"
