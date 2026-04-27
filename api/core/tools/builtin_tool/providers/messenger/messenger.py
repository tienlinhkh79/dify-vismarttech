from __future__ import annotations

from typing import Any

import httpx

from core.tools.builtin_tool.provider import BuiltinToolProviderController
from core.tools.errors import ToolProviderCredentialValidationError


class MessengerProvider(BuiltinToolProviderController):
    def _validate_credentials(self, user_id: str, credentials: dict[str, Any]) -> None:
        app_id = str(credentials.get("app_id", "")).strip()
        app_secret = str(credentials.get("app_secret", "")).strip()
        page_id = str(credentials.get("page_id", "")).strip()
        page_access_token = str(credentials.get("page_access_token", "")).strip()
        graph_api_version = str(credentials.get("graph_api_version", "v23.0")).strip() or "v23.0"
        if not app_id:
            raise ToolProviderCredentialValidationError("Missing app_id")
        if not app_secret:
            raise ToolProviderCredentialValidationError("Missing app_secret")
        if not page_id:
            raise ToolProviderCredentialValidationError("Missing page_id")
        if not page_access_token:
            raise ToolProviderCredentialValidationError("Missing page_access_token")

        try:
            response = httpx.get(
                f"https://graph.facebook.com/{graph_api_version}/me",
                params={"fields": "id,name", "access_token": page_access_token},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("id"):
                raise ToolProviderCredentialValidationError("Messenger token validation failed: missing page id")
            if str(data.get("id")) != page_id:
                raise ToolProviderCredentialValidationError("Messenger token does not match selected page")
        except ToolProviderCredentialValidationError:
            raise
        except Exception as e:
            raise ToolProviderCredentialValidationError(f"Messenger credential validation failed: {e}") from e
