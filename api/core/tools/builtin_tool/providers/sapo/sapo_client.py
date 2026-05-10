"""Sapo REST API client with access-token based authentication.

This client targets the store-scoped API host:
https://{store}.mysapo.net
and authenticates with the X-Sapo-Access-Token header.
"""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT = 30


class SapoAPIError(Exception):
    """Raised when a Sapo API request fails."""

    def __init__(self, message: str, status_code: int | None = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class SapoClient:
    """Small HTTP client for Sapo store APIs."""

    def __init__(self, store: str, access_token: str) -> None:
        if not store or not access_token:
            raise ValueError("store and access_token are required")
        self._store = store.strip().replace("https://", "").replace("http://", "")
        self._access_token = access_token
        self._http = httpx.Client(base_url=f"https://{self._store}", timeout=DEFAULT_TIMEOUT)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Sapo-Access-Token": self._access_token,
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
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
            raise SapoAPIError(
                message=f"Sapo API error {exc.response.status_code}: {error_body}",
                status_code=exc.response.status_code,
                response_data=error_body,
            ) from exc
        if not resp.content:
            return None
        return resp.json()

    def close(self) -> None:
        self._http.close()
