"""Map NotebookLM answers to Dify External Knowledge retrieval records."""

from __future__ import annotations

import os
import re
from typing import Any, TypedDict

from app.mcp_client import NotebookLMQueryResult, NotebookLMSource

IMAGE_TITLES = {
    "square_garden_villa.png": "Square Garden Villa",
    "modern_1_story_house_7x30.png": "Mẫu thiết kế nhà 1 tầng 7x30",
    "interior_living_kitchen_7x30.png": "Phối cảnh nội thất phòng khách - bếp 7x30",
    "modern_3_story_townhouse.png": "Nhà phố 3 tầng hiện đại",
    "modern_green_office.png": "Văn phòng xanh hiện đại",
    "novaland_model_apartment.png": "Căn hộ mẫu Novaland",
    "open_concept_living_room.png": "Phòng khách không gian mở",
    "tan_binh_small_townhouse.png": "Nhà phố nhỏ Tân Bình",
}

KEYWORD_TO_IMAGE = {
    "square garden villa": "square_garden_villa.png",
    "biệt thự sân vườn": "square_garden_villa.png",
    "nhà 1 tầng 7x30": "modern_1_story_house_7x30.png",
    "1 tầng 7x30": "modern_1_story_house_7x30.png",
    "nhà 7x30": "modern_1_story_house_7x30.png",
    "nội thất 7x30": "interior_living_kitchen_7x30.png",
    "phòng khách bếp 7x30": "interior_living_kitchen_7x30.png",
    "phố 3 tầng": "modern_3_story_townhouse.png",
    "nhà 3 tầng": "modern_3_story_townhouse.png",
    "văn phòng xanh": "modern_green_office.png",
    "novaland": "novaland_model_apartment.png",
    "phòng khách mở": "open_concept_living_room.png",
    "tân bình": "tan_binh_small_townhouse.png",
}


def clean_studio_references(text: str) -> str:
    """Clean up NotebookLM specific references to Studio panel so answers read naturally."""
    cleaned = re.sub(
        r"\(?(?:Lưu ý:\s*)?(?:Bạn\s+cũng\s+có\s+thể\s+|Bạn\s+có\s+thể\s+)?(?:click|nhấp|xem)\s+(?:trực tiếp\s+)?vào\s+các\s+tệp\s+ảnh[^\)\n]*ở\s+bảng\s+Studio[^\)\n]*\)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"tại\s+(?:góc|bảng)\s+\*?\*?Studio\*?\*?\s*(?:\([^)]*\))?\s*dưới\s+tệp\s*",
        "với tệp ảnh ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\((?:góc|bảng)\s+bên\s+phải\s+màn\s+hình\)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"ở\s+bảng\s+Studio\s+(?:bên\s+phải|góc\s+phải)",
        "trong hồ sơ thiết kế",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"tại\s+(?:góc|bảng)\s+\*?\*?Studio\*?\*?",
        "trong hồ sơ thiết kế",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def enrich_answer_with_images(
    answer: str,
    *,
    image_dir: str = "",
    public_image_url: str = "",
) -> str:
    if not answer.strip():
        return answer

    cleaned = clean_studio_references(answer)
    public_url = (public_image_url or "https://chatbotai.vismarttech.com/notebooklm-images").rstrip("/")

    available_files: set[str] = set()
    if image_dir and os.path.exists(image_dir):
        try:
            available_files = {
                f
                for f in os.listdir(image_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
            }
        except Exception:
            pass

    if not available_files:
        available_files = set(IMAGE_TITLES.keys())

    matched_images: list[str] = []
    lowered_text = cleaned.lower()

    for filename in sorted(available_files):
        stem = os.path.splitext(filename)[0].lower()
        if filename.lower() in lowered_text or stem in lowered_text:
            if filename not in matched_images:
                matched_images.append(filename)

    for keyword, filename in KEYWORD_TO_IMAGE.items():
        if filename in available_files and filename not in matched_images:
            if keyword in lowered_text:
                matched_images.append(filename)

    if not matched_images:
        return cleaned

    image_markdowns: list[str] = []
    for filename in matched_images:
        img_url = f"{public_url}/{filename}"
        if img_url in cleaned:
            continue
        title = IMAGE_TITLES.get(filename, filename)
        image_markdowns.append(f"![{title}]({img_url})")

    if not image_markdowns:
        return cleaned

    embed_block = "\n\n" + "\n\n".join(image_markdowns)
    return cleaned + embed_block


class RetrievalSetting(TypedDict, total=False):
    top_k: int
    score_threshold: float


class RetrievalRequest(TypedDict, total=False):
    query: str
    knowledge_id: str
    retrieval_setting: RetrievalSetting
    metadata_condition: dict[str, Any] | None


class RetrievalRecord(TypedDict):
    content: str
    score: float
    title: str
    metadata: dict[str, Any]


class RetrievalResponse(TypedDict):
    records: list[RetrievalRecord]


def map_query_result_to_records(
    result: NotebookLMQueryResult,
    *,
    notebook_id: str,
    top_k: int = 3,
    image_dir: str = "",
    public_image_url: str = "",
) -> RetrievalResponse:
    records: list[RetrievalRecord] = []

    answer_text = result.answer.strip()
    if answer_text:
        enriched_content = enrich_answer_with_images(
            answer_text,
            image_dir=image_dir,
            public_image_url=public_image_url,
        )
        records.append(
            _build_record(
                content=enriched_content,
                score=1.0,
                title="NotebookLM answer",
                metadata={
                    "source": "notebooklm",
                    "notebook_id": notebook_id,
                    "record_type": "synthesized_answer",
                    "citations": [_source_to_dict(source) for source in result.sources],
                },
            )
        )

    remaining = max(top_k - len(records), 0)
    for source in result.sources[:remaining]:
        excerpt = source.excerpt.strip()
        if not excerpt:
            continue
        records.append(
            _build_record(
                content=excerpt,
                score=max(0.5, 1.0 - (source.index * 0.05)),
                title=source.title,
                metadata={
                    "source": "notebooklm",
                    "notebook_id": notebook_id,
                    "record_type": "citation",
                    "citation_index": source.index,
                    "url": source.url,
                },
            )
        )

    return {"records": records[:top_k]}


def _build_record(
    *,
    content: str,
    score: float,
    title: str,
    metadata: dict[str, Any],
) -> RetrievalRecord:
    return {
        "content": content,
        "score": score,
        "title": title,
        "metadata": metadata,
    }


def _source_to_dict(source: NotebookLMSource) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "index": source.index,
        "title": source.title,
        "excerpt": source.excerpt,
    }
    if source.url:
        payload["url"] = source.url
    return payload


def parse_top_k(retrieval_setting: RetrievalSetting | None) -> int:
    if not retrieval_setting:
        return 3
    top_k = retrieval_setting.get("top_k")
    if isinstance(top_k, int) and top_k > 0:
        return top_k
    return 3
