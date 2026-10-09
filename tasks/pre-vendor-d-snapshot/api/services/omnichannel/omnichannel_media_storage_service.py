"""Outbound media uploads for omnichannel inbox composer.

Default implementation stores files via :class:`services.file_service.FileService` and
returns a signed HTTPS URL suitable for Meta Messenger / Instagram DM attachments.
Swap or extend this module when an external object-storage provider is configured.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from extensions.ext_database import db
from models import Account
from services.file_service import FileService

_AttachmentType = Literal["image", "video", "audio", "file"]


class OmnichannelMediaUploadResult(TypedDict):
    url: str
    attachment_type: _AttachmentType
    file_id: str
    name: str


class OmnichannelMediaStorageService:
    @staticmethod
    def _guess_attachment_type(mimetype: str, extension: str) -> _AttachmentType:
        mime = (mimetype or "").lower()
        ext = (extension or "").lower()
        if mime.startswith("image/") or ext in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"}:
            return "image"
        if mime.startswith("video/") or ext in {"mp4", "mov", "webm", "mkv"}:
            return "video"
        if mime.startswith("audio/") or ext in {"mp3", "wav", "ogg", "m4a", "aac"}:
            return "audio"
        return "file"

    @classmethod
    def upload(
        cls,
        *,
        filename: str,
        content: bytes,
        mimetype: str,
        user: Account,
    ) -> OmnichannelMediaUploadResult:
        upload_file = FileService(db.engine).upload_file(
            filename=filename,
            content=content,
            mimetype=mimetype,
            user=user,
        )
        url = (upload_file.source_url or "").strip()
        if not url.lower().startswith("https://"):
            raise ValueError("Uploaded media must be reachable via an HTTPS URL")
        attachment_type = cls._guess_attachment_type(
            upload_file.mime_type or mimetype,
            upload_file.extension or "",
        )
        return {
            "url": url,
            "attachment_type": attachment_type,
            "file_id": upload_file.id,
            "name": upload_file.name,
        }
