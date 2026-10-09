from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NOTEBOOKLM_PROXY_API_KEY", "test-secret-key")
    monkeypatch.setenv("NOTEBOOKLM_MCP_URL", "http://notebooklm-mcp:8010/mcp")
    import app.main as main_module

    main_module._settings = None
    main_module._mcp_client = None
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_retrieval_requires_bearer(client: TestClient) -> None:
    response = client.post(
        "/retrieval",
        json={"query": "hello", "knowledge_id": "notebook-1"},
    )
    assert response.status_code == 401


def test_retrieval_accepts_empty_body_for_dify_validation(client: TestClient) -> None:
    response = client.post(
        "/retrieval",
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"records": []}


def test_retrieval_rejects_invalid_bearer(client: TestClient) -> None:
    response = client.post(
        "/retrieval",
        json={"query": "hello", "knowledge_id": "notebook-1"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401
