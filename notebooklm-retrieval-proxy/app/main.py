"""FastAPI service implementing Dify External Knowledge `/retrieval` for NotebookLM."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import Settings, load_settings
from app.mcp_client import MCPAuthError, MCPClientError, MCPTimeoutError, NotebookLMMCPClient, new_mcp_client
from app.retrieval import RetrievalResponse, map_query_result_to_records, parse_top_k

logger = logging.getLogger(__name__)

app = FastAPI(title="NotebookLM Retrieval Proxy", version="0.1.0")

_image_dir = os.environ.get("NOTEBOOKLM_IMAGE_DIR", "/app/data/images")
os.makedirs(_image_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=_image_dir), name="images")


class RetrievalSettingModel(BaseModel):
    top_k: int | None = Field(default=3, ge=1, le=20)
    score_threshold: float | None = Field(default=0.0, ge=0.0, le=1.0)


class RetrievalRequestModel(BaseModel):
    query: str = Field(min_length=1)
    knowledge_id: str = Field(min_length=1)
    retrieval_setting: RetrievalSettingModel | None = None
    metadata_condition: dict[str, Any] | None = None


_settings: Settings | None = None
_mcp_client: NotebookLMMCPClient | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def get_mcp_client(settings: Settings) -> NotebookLMMCPClient:
    """Reuse one MCP session — notebooklm-mcp HTTP transport allows a single connection."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = new_mcp_client(
            settings.mcp_url,
            timeout_seconds=settings.request_timeout_seconds,
            answer_timeout_ms=settings.answer_timeout_ms,
        )
    return _mcp_client


def verify_bearer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.proxy_api_key:
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/retrieval", dependencies=[Depends(verify_bearer)])
async def retrieval(request: Request, settings: Settings = Depends(get_settings)) -> RetrievalResponse:
    try:
        payload = await request.json()
    except Exception:
        return {"records": []}

    if not isinstance(payload, dict) or not payload:
        return {"records": []}

    try:
        body = RetrievalRequestModel.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    notebook_id = body.knowledge_id.strip()
    query = body.query.strip()
    top_k = parse_top_k(body.retrieval_setting.model_dump() if body.retrieval_setting else None)

    client = get_mcp_client(settings)

    try:
        result = client.ask_question(notebook_id=notebook_id, question=query, source_format="json")
    except MCPAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except MCPTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except MCPClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return map_query_result_to_records(
        result,
        notebook_id=notebook_id,
        top_k=top_k,
        image_dir=settings.image_dir,
        public_image_url=settings.public_image_url,
    )
