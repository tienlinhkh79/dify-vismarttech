"""Builtin Sapo provider credential validation."""

from typing import Any

from core.tools.builtin_tool.provider import BuiltinToolProviderController
from core.tools.builtin_tool.providers.sapo.sapo_client import SapoClient
from core.tools.errors import ToolProviderCredentialValidationError


class SapoProvider(BuiltinToolProviderController):
    def _validate_credentials(self, user_id: str, credentials: dict[str, Any]) -> None:
        """Validate store access token by calling a lightweight endpoint."""
        client = None
        try:
            client = SapoClient(
                store=credentials.get("store", ""),
                access_token=credentials.get("access_token", ""),
            )
            client.get("/admin/products/count.json")
        except Exception as e:
            raise ToolProviderCredentialValidationError(f"Sapo credential validation failed: {e}") from e
        finally:
            if client is not None:
                client.close()
