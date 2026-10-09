from __future__ import annotations

import pytest

from app.mcp_client import NotebookLMMCPClient
from app.retrieval import map_query_result_to_records, parse_top_k
from app.mcp_client import NotebookLMQueryResult, NotebookLMSource


class TestCleanAnswer:
    def test_strips_ai_marker_prefix(self) -> None:
        raw = (
            "[AI-GENERATED via Gemini 2.5 (NotebookLM) — answer synthesized from sources]\n\n"
            "Actual answer text."
        )
        assert NotebookLMMCPClient.clean_answer(raw) == "Actual answer text."


class TestRetrievalMapper:
    def test_maps_answer_and_citations(self) -> None:
        result = NotebookLMQueryResult(
            answer="Main grounded answer.",
            sources=[
                NotebookLMSource(index=1, title="Doc A", excerpt="Excerpt A", url="https://example.com/a"),
                NotebookLMSource(index=2, title="Doc B", excerpt="Excerpt B"),
            ],
        )

        payload = map_query_result_to_records(result, notebook_id="notebook-123", top_k=3)

        assert len(payload["records"]) == 3
        assert payload["records"][0]["content"] == "Main grounded answer."
        assert payload["records"][0]["metadata"]["notebook_id"] == "notebook-123"
        assert payload["records"][1]["title"] == "Doc A"
        assert payload["records"][2]["metadata"]["record_type"] == "citation"

    def test_top_k_limits_records(self) -> None:
        result = NotebookLMQueryResult(
            answer="Answer only.",
            sources=[
                NotebookLMSource(index=1, title="S1", excerpt="E1"),
                NotebookLMSource(index=2, title="S2", excerpt="E2"),
            ],
        )

        payload = map_query_result_to_records(result, notebook_id="nb", top_k=1)

        assert len(payload["records"]) == 1
        assert payload["records"][0]["content"] == "Answer only."


class TestParseTopK:
    def test_defaults_to_three(self) -> None:
        assert parse_top_k(None) == 3

    def test_uses_retrieval_setting(self) -> None:
        assert parse_top_k({"top_k": 5}) == 5


class TestImageEnricher:
    def test_enriches_answer_with_image_markdown(self) -> None:
        raw = "Mẫu thiết kế Square Garden Villa đã có sẵn tại bảng **Studio** (góc bên phải màn hình) dưới tệp `square_garden_villa.png`."
        result = NotebookLMQueryResult(answer=raw, sources=[])
        payload = map_query_result_to_records(
            result,
            notebook_id="nb-123",
            top_k=1,
            public_image_url="https://chatbotai.vismarttech.com/notebooklm-images",
        )
        content = payload["records"][0]["content"]
        assert "![Square Garden Villa](https://chatbotai.vismarttech.com/notebooklm-images/square_garden_villa.png)" in content
        assert "góc bên phải màn hình" not in content
