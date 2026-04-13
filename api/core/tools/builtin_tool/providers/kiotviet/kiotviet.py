from typing import Any

from core.tools.builtin_tool.provider import BuiltinToolProviderController
from core.tools.builtin_tool.providers.kiotviet.kiotviet_client import KiotVietAuthError, KiotVietClient
from core.tools.errors import ToolProviderCredentialValidationError


class KiotvietProvider(BuiltinToolProviderController):
    def _validate_credentials(self, user_id: str, credentials: dict[str, Any]) -> None:
        """Validate credentials by obtaining token and calling a lightweight API."""
        client = None
        try:
            client = KiotVietClient(
                client_id=credentials.get("client_id", ""),
                client_secret=credentials.get("client_secret", ""),
                retailer_name=credentials.get("retailer_name", ""),
            )
            # Step 1: validate OAuth client credentials.
            client._get_valid_token()
            # Step 2: validate retailer context/permissions.
            # Token can be valid while retailer header is invalid, which later causes unauthorized tool calls.
            client.get("/branches", {"pageSize": 1})
        except KiotVietAuthError as e:
            raise ToolProviderCredentialValidationError(f"KiotViet authentication failed: {e}") from e
        except Exception as e:
            raise ToolProviderCredentialValidationError(f"KiotViet credential validation failed: {e}") from e
        finally:
            if client is not None:
                client.close()
