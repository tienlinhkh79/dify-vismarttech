from __future__ import annotations

import json

import httpx

from app.mcp_client import MCPClientError, NotebookLMMCPClient


def test_parse_json_response_sse() -> None:
    payload = {"result": {"content": [{"type": "text", "text": "ok"}]}, "jsonrpc": "2.0", "id": 1}
    body = f"event: message\ndata: {json.dumps(payload)}\n\n"
    response = httpx.Response(200, text=body, request=httpx.Request("POST", "http://example/mcp"))

    parsed = NotebookLMMCPClient._parse_json_response(response)

    assert parsed["id"] == 1


def test_unwrap_tool_result_success_wrapper() -> None:
    result = {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"success": True, "data": {"authenticated": False, "status": "ok"}}),
            }
        ]
    }

    unwrapped = NotebookLMMCPClient._unwrap_tool_result(result)

    assert unwrapped["authenticated"] is False
    assert unwrapped["status"] == "ok"


def test_unwrap_tool_result_failure_raises() -> None:
    result = {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"success": False, "error": "browser missing"}),
            }
        ]
    }

    try:
        NotebookLMMCPClient._unwrap_tool_result(result)
    except MCPClientError as exc:
        assert "browser missing" in str(exc)
    else:
        raise AssertionError("expected MCPClientError")
