"""Unit tests for omnichannel media upload type detection."""

from services.omnichannel.omnichannel_media_storage_service import OmnichannelMediaStorageService


def test_guess_attachment_type_image() -> None:
    assert OmnichannelMediaStorageService._guess_attachment_type("image/png", "png") == "image"


def test_guess_attachment_type_video() -> None:
    assert OmnichannelMediaStorageService._guess_attachment_type("video/mp4", "mp4") == "video"


def test_guess_attachment_type_audio() -> None:
    assert OmnichannelMediaStorageService._guess_attachment_type("audio/mpeg", "mp3") == "audio"


def test_guess_attachment_type_file_fallback() -> None:
    assert OmnichannelMediaStorageService._guess_attachment_type("application/pdf", "pdf") == "file"
