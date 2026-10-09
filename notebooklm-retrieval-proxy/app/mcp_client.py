"""Minimal Streamable-HTTP MCP client for notebooklm-mcp."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MCP_SESSION_HEADER = "mcp-session-id"
PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "notebooklm-retrieval-proxy"
CLIENT_VERSION = "0.1.0"

AI_MARKER_PATTERN = re.compile(
    r"^\[AI-GENERATED via Gemini[^\]]*\]\s*",
    re.IGNORECASE | re.DOTALL,
)


class MCPClientError(Exception):
    """Base MCP client error."""


class MCPAuthError(MCPClientError):
    """NotebookLM is not authenticated."""


class MCPTimeoutError(MCPClientError):
    """NotebookLM answer timed out."""


@dataclass
class NotebookLMSource:
    index: int
    title: str
    excerpt: str
    url: str | None = None


@dataclass
class NotebookLMQueryResult:
    answer: str
    sources: list[NotebookLMSource] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class NotebookLMMCPClient:
    def __init__(
        self,
        mcp_url: str,
        *,
        timeout_seconds: float = 120.0,
        answer_timeout_ms: int = 600_000,
    ) -> None:
        self._mcp_url = mcp_url
        self._timeout_seconds = timeout_seconds
        self._answer_timeout_ms = answer_timeout_ms
        self._session_id: str | None = None
        self._request_id = 0
        self._http = httpx.Client(timeout=self._timeout_seconds)

    def ask_question(
        self,
        *,
        notebook_id: str,
        question: str,
        source_format: str = "json",
    ) -> NotebookLMQueryResult:
        try:
            payload = self._call_tool(
                "notebook_query",
                {
                    "notebook_id": notebook_id,
                    "query": question,
                },
            )
            return self._parse_ask_question_result(payload)
        except Exception as exc:
            logger.warning("notebook_query failed or not found (%s), falling back to ask_question", exc)
            payload = self._call_tool(
                "ask_question",
                {
                    "question": question,
                    "notebook_id": notebook_id,
                    "source_format": source_format,
                },
            )
            return self._parse_ask_question_result(payload)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                self._ensure_session()
                response = self._post(
                    {
                        "jsonrpc": "2.0",
                        "id": self._next_id(),
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    }
                )
                if response.status_code == 400 and attempt == 0:
                    logger.warning("MCP session expired, re-initializing")
                    self._session_id = None
                    continue
                response.raise_for_status()
                body = self._parse_json_response(response)
                if "error" in body:
                    raise MCPClientError(str(body["error"]))
                result = body.get("result") or {}
                return self._unwrap_tool_result(result)
            except httpx.TimeoutException as exc:
                raise MCPTimeoutError("NotebookLM request timed out") from exc
            except MCPClientError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    self._session_id = None
                    continue
                raise MCPClientError(str(exc)) from exc
        raise MCPClientError(str(last_error or "MCP tool call failed"))

    def _ensure_session(self) -> None:
        if getattr(self, "_initialized", False):
            return

        try:
            init_response = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
                    },
                },
                include_session=False,
            )
            init_response.raise_for_status()
            self._session_id = init_response.headers.get(MCP_SESSION_HEADER)
            self._initialized = True

            try:
                self._post(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {},
                    },
                    include_session=True,
                )
            except Exception:
                pass
        except Exception as exc:
            logger.warning("MCP initialize failed (%s), proceeding in stateless mode", exc)
            self._initialized = True

    def _post(self, payload: dict[str, Any], *, include_session: bool = True) -> httpx.Response:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if include_session and self._session_id:
            headers[MCP_SESSION_HEADER] = self._session_id

        return self._http.post(self._mcp_url, headers=headers, json=payload)

    @staticmethod
    def _parse_json_response(response: httpx.Response) -> dict[str, Any]:
        text = response.text.strip()
        if not text:
            return {}
        if text.startswith("{"):
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        for line in text.split("\n"):
            if line.startswith("data: "):
                parsed = json.loads(line[6:])
                return parsed if isinstance(parsed, dict) else {}
        raise MCPClientError(f"Unexpected MCP response: {text[:200]}")

    @staticmethod
    def _unwrap_tool_result(result: dict[str, Any]) -> dict[str, Any]:
        if result.get("isError"):
            message = NotebookLMMCPClient._extract_text_content(result) or "MCP tool returned an error"
            lowered = message.lower()
            if "auth" in lowered or "login" in lowered or "sign in" in lowered:
                raise MCPAuthError(message)
            raise MCPClientError(message)

        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured

        text = NotebookLMMCPClient._extract_text_content(result)
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                if parsed.get("success") is False:
                    error_message = str(parsed.get("error") or "MCP tool returned an error")
                    lowered = error_message.lower()
                    if "auth" in lowered or "login" in lowered or "sign in" in lowered:
                        raise MCPAuthError(error_message)
                    raise MCPClientError(error_message)
                data = parsed.get("data")
                if parsed.get("success") and isinstance(data, dict):
                    return data
                return parsed
        except json.JSONDecodeError:
            return {"answer": text}
        return {"answer": text}

    @staticmethod
    def _extract_text_content(result: dict[str, Any]) -> str:
        content = result.get("content") or []
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    @classmethod
    def _parse_ask_question_result(cls, payload: dict[str, Any]) -> NotebookLMQueryResult:
        answer_raw = payload.get("answer") or payload.get("text") or payload.get("content") or ""
        if isinstance(answer_raw, dict):
            answer_text = json.dumps(answer_raw, ensure_ascii=False)
        else:
            answer_text = str(answer_raw)

        answer_text = cls.clean_answer(answer_text)

        sources: list[NotebookLMSource] = []
        raw_sources = payload.get("sources") or []
        if isinstance(raw_sources, list):
            for idx, item in enumerate(raw_sources, start=1):
                if not isinstance(item, dict):
                    continue
                sources.append(
                    NotebookLMSource(
                        index=int(item.get("index") or idx),
                        title=str(item.get("title") or item.get("name") or f"Source {idx}"),
                        excerpt=str(item.get("excerpt") or item.get("snippet") or ""),
                        url=item.get("url") if isinstance(item.get("url"), str) else None,
                    )
                )

        return NotebookLMQueryResult(answer=answer_text, sources=sources, raw=payload)

    @staticmethod
    def clean_answer(text: str) -> str:
        cleaned = AI_MARKER_PATTERN.sub("", text.strip())
        return cleaned.strip()


def new_mcp_client(mcp_url: str, *, timeout_seconds: float, answer_timeout_ms: int) -> NotebookLMMCPClient:
    _ = answer_timeout_ms  # reserved for future per-call timeout wiring
    return NotebookLMMCPClient(
        mcp_url=mcp_url,
        timeout_seconds=timeout_seconds,
        answer_timeout_ms=answer_timeout_ms,
    )
