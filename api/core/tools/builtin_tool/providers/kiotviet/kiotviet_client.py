"""KiotViet API client for Dify, ported from kiotviet-client-sdk (TypeScript)."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx


TOKEN_URL = "https://id.kiotviet.vn/connect/token"
BASE_URL = "https://public.kiotapi.com"
DEFAULT_SCOPE = "PublicApi.Access"
TOKEN_BUFFER_SECONDS = 60
DEFAULT_TIMEOUT = 30


class KiotVietAuthError(Exception):
    """Raised when authentication with KiotViet fails."""


class KiotVietAPIError(Exception):
    """Raised when a KiotViet API call fails."""

    def __init__(self, message: str, status_code: int | None = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class KiotVietClient:
    """Python client for KiotViet Public API.

    Mirrors the architecture of the TypeScript kiotviet-client-sdk:
    - OAuth 2.0 client_credentials authentication
    - Automatic token caching and refresh
    - Bearer token + Retailer header on every request
    """

    def __init__(self, client_id: str, client_secret: str, retailer_name: str) -> None:
        if not client_id or not client_secret or not retailer_name:
            raise ValueError("client_id, client_secret, and retailer_name are required")

        self._client_id = client_id
        self._client_secret = client_secret
        self._retailer_name = retailer_name

        self._access_token: str | None = None
        self._token_expires_at: float | None = None

        self._http = httpx.Client(
            base_url=BASE_URL,
            timeout=DEFAULT_TIMEOUT,
        )

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_valid_token(self) -> str:
        now = time.time()
        if self._access_token and self._token_expires_at and self._token_expires_at > now:
            return self._access_token
        return self._fetch_new_token()

    def _fetch_new_token(self) -> str:
        try:
            resp = httpx.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": DEFAULT_SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()
            self._access_token = body["access_token"]
            expires_in: int = body.get("expires_in", 3600)
            self._token_expires_at = time.time() + (expires_in - TOKEN_BUFFER_SECONDS)
            return self._access_token  # type: ignore[return-value]
        except httpx.HTTPStatusError as exc:
            data = exc.response.json() if exc.response.content else {}
            msg = data.get("error_description") or data.get("error") or "Failed to fetch access token"
            raise KiotVietAuthError(msg) from exc
        except Exception as exc:
            raise KiotVietAuthError(f"Token request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self._get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Retailer": self._retailer_name,
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        resp = self._http.get(path, headers=self._headers(), params=params)
        return self._handle_response(resp)

    def post(self, path: str, data: Any = None) -> Any:
        resp = self._http.post(path, headers=self._headers(), json=data)
        return self._handle_response(resp)

    def put(self, path: str, data: Any = None) -> Any:
        resp = self._http.put(path, headers=self._headers(), json=data)
        return self._handle_response(resp)

    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        resp = self._http.delete(path, headers=self._headers(), params=params)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> Any:
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                error_body = exc.response.json()
            except Exception:
                error_body = exc.response.text
            raise KiotVietAPIError(
                message=f"KiotViet API error {exc.response.status_code}: {error_body}",
                status_code=exc.response.status_code,
                response_data=error_body,
            ) from exc
        if not resp.content:
            return None
        return resp.json()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._http.close()
