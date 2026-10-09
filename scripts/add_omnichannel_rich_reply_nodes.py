"""Insert Code nodes that convert LLM output into omnichannel rich-reply JSON.

Targets draft workflows for:
- Trợ lý Ai Việt Automate (5556270c…)
- Trợ lý tuyển dụng / Vieclamtop (756d906f…)
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg2

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

APPS: dict[str, dict[str, Any]] = {
    "5556270c-c1e9-4454-9212-f66b281ead51": {
        "draft_workflow_id": "546dbee6-7e4d-418f-b21b-e991705f4ea7",
        "code_node_id": "178200001001",
        "llm_node_ids": ["llm"],
        "enable_structured_output": True,
        "hero_image_url": "",
        "structured_prompt_suffix": (
            "\n\nĐịnh dạng trả lời cho Messenger (structured output — KHÔNG viết JSON vào phần text):\n"
            "- TUYỆT ĐỐI không xuất JSON/markdown trong text; chỉ nói chuyện tự nhiên qua field ai_reply.\n"
            "- Tư vấn dịch vụ / FAQ: display_type = service_cards, ai_reply = 1-2 câu ngắn, products = [], "
            "quick_replies = 2-4 lựa chọn NGẮN GỌN (tối đa 20 ký tự, vd: Tư vấn mô hình, Xem quy trình, Liên hệ).\n"
            "- Có sản phẩm cụ thể từ kiến thức: display_type = product_grid, products đầy đủ "
            "(id, product_name, price, image_url, detail_url), quick_replies = 2-3 nút phụ.\n"
            "- Luôn có quick_replies khi có thể — đây sẽ hiện thành nút bấm đẹp trên Messenger."
        ),
    },
    "756d906f-3b82-4087-a6dd-e45e9745d04f": {
        "draft_workflow_id": "2441f8bf-f16e-4668-bed8-cb8aeb784a46",
        "code_node_id": "178200002001",
        "llm_node_ids": [
            "178100008001",  # LLM Gợi ý việc
            "178100008003",  # LLM Chi tiết tin
            "178100008002",  # LLM FAQ
            "178100008004",  # LLM CV
            "178100008005",  # LLM NTD
            "1711528917469",  # LLM General
        ],
        "llm_to_answer": {
            "178100008001": "178100009001",
            "178100008003": "178100009003",
            "178100008002": "178100009002",
            "178100008004": "178100009004",
            "178100008005": "178100009005",
            "1711528917469": "1711528919501",
        },
        "enable_structured_output": False,
    },
}

RICH_REPLY_CODE = r'''
import json
import re
import unicodedata


def _clamp_intro(text: str, limit: int = 480) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _slug(label: str) -> str:
    folded = unicodedata.normalize("NFKD", label)
    ascii_text = "".join(ch for ch in folded if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return (value or label)[:40]


def _fmt_price(value) -> str:
    if isinstance(value, (int, float)):
        return f"{int(value):,}đ".replace(",", ".")
    return str(value or "").strip()


def _normalize_structured(data: dict) -> dict:
    quick = data.get("quick_replies")
    if quick is None:
        quick = data.get("quickreplies")
    products = data.get("products")
    if products is None:
        products = []
    return {
        "display_type": str(data.get("display_type") or data.get("displaytype") or "").strip(),
        "ai_reply": str(data.get("ai_reply") or data.get("aireply") or data.get("text") or "").strip(),
        "products": products if isinstance(products, list) else [],
        "quick_replies": quick if isinstance(quick, list) else [],
    }


def _strip_structured_leak(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    parsed = _parse_embedded_structured(value)
    if parsed:
        ai_reply = str(parsed.get("ai_reply") or parsed.get("aireply") or "").strip()
        if ai_reply:
            return ai_reply
    markers = (
        '","display_type"',
        '","displaytype"',
        '","products"',
        '","quick_replies"',
        '","quickreplies"',
    )
    cut_at = len(value)
    for marker in markers:
        idx = value.find(marker)
        if idx >= 0:
            cut_at = min(cut_at, idx)
    if cut_at < len(value):
        value = value[:cut_at].rstrip(" ,\"")
    if value.startswith("{") and not value.endswith("}"):
        value = ""
    return value.strip()


def _parse_embedded_structured(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    start = raw.find("{")
    if start < 0:
        return None
    chunk = raw[start:]
    try:
        parsed = json.loads(chunk)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _buttons_from_quick_replies(quick_replies: list) -> list[dict]:
    buttons: list[dict] = []
    for raw in quick_replies[:4]:
        label = str(raw).strip()
        if not label:
            continue
        buttons.append({"title": label, "action": "postback", "payload": _slug(label)})
    return buttons


def _build_product_cards(data: dict) -> dict | None:
    products = data.get("products") or []
    if not isinstance(products, list) or not products:
        return None
    intro = str(data.get("ai_reply") or "").strip()
    cards = []
    for item in products[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("product_name") or item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        image_url = str(item.get("image_url") or item.get("image") or "").strip()
        if not image_url:
            continue
        card: dict = {"title": title, "image_url": image_url}
        subtitle = _fmt_price(item.get("price") or item.get("salary") or item.get("subtitle"))
        if not subtitle:
            subtitle = str(item.get("subtitle") or item.get("description") or "").strip()[:80]
        if subtitle:
            card["subtitle"] = subtitle
        detail_url = str(item.get("detail_url") or item.get("url") or item.get("link") or "").strip()
        if detail_url:
            card["default_url"] = detail_url
            card["buttons"] = [{"title": "Xem chi tiết", "action": "url", "url": detail_url}]
        else:
            card["buttons"] = [{"title": "Tư vấn", "action": "postback", "payload": _slug(title)}]
        cards.append(card)
    if not cards:
        return None
    payload: dict = {
        "type": "cards",
        "text": _clamp_intro(intro or "Em gợi ý một số lựa chọn phù hợp ạ:"),
        "cards": cards,
    }
    footer = _buttons_from_quick_replies(data.get("quick_replies") or [])
    if footer:
        payload["buttons"] = footer
    return payload


def _build_hero_menu(data: dict, hero_image: str) -> dict | None:
    image = (hero_image or "").strip()
    if not image:
        return None
    quick = data.get("quick_replies") or []
    card_buttons = _buttons_from_quick_replies(quick[:3])
    if len(card_buttons) < 2:
        return None
    intro = str(data.get("ai_reply") or "").strip()
    card = {
        "title": "Việt Automate",
        "subtitle": _clamp_intro(intro, 80) or "Trợ lý AI & workflow tự động",
        "image_url": image,
        "buttons": card_buttons,
    }
    payload: dict = {"type": "cards", "cards": [card]}
    footer = _buttons_from_quick_replies(quick[3:])
    if footer:
        payload["buttons"] = footer
    return payload


def _build_actions(data: dict, *, fallback_text: str = "") -> dict | None:
    intro = str(data.get("ai_reply") or "").strip() or _strip_structured_leak(fallback_text)
    buttons = _buttons_from_quick_replies(data.get("quick_replies") or [])
    if intro and buttons:
        return {"type": "actions", "text": _clamp_intro(intro), "buttons": buttons}
    if buttons:
        return {
            "type": "actions",
            "text": _clamp_intro(intro or "Anh/chị chọn giúp em ạ:"),
            "buttons": buttons,
        }
    if intro:
        return {
            "type": "actions",
            "text": _clamp_intro(intro),
            "buttons": [
                {"title": "Tư vấn thêm", "action": "postback", "payload": _slug("Tư vấn thêm")},
                {"title": "Liên hệ", "action": "postback", "payload": _slug("Liên hệ")},
            ],
        }
    return None


def _build_from_structured(data: dict, *, fallback_text: str = "", hero_image: str = "") -> dict | None:
    normalized = _normalize_structured(data)
    display = normalized["display_type"].lower().replace("_", "")

    if display in {"productgrid", "products"}:
        cards = _build_product_cards(normalized)
        if cards:
            return cards

    if display in {"servicecards", "servicemenu", "actions", "faq", "textonly"}:
        actions = _build_actions(normalized, fallback_text=fallback_text)
        if actions:
            return actions

    hero = _build_hero_menu(normalized, hero_image)
    if hero:
        return hero

    actions = _build_actions(normalized, fallback_text=fallback_text)
    if actions:
        return actions

    return None


def _build_job_cards_from_text(text: str) -> dict | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cards = []
    for line in lines:
        if not line[0].isdigit() and not line.startswith("-"):
            continue
        cleaned = line.lstrip("0123456789.-) ").strip()
        if len(cleaned) < 8:
            continue
        title = cleaned.split("|")[0].split("—")[0].strip()[:80]
        if title:
            cards.append({"title": title, "subtitle": cleaned[len(title):].strip(" -—|")[:120]})
        if len(cards) >= 5:
            break
    if len(cards) < 2:
        return None
    intro_lines = [ln for ln in lines if ln not in {c.get("title", "") for c in cards}][:2]
    intro = " ".join(intro_lines)[:300] or "Em gợi ý một số vị trí phù hợp ạ:"
    return {
        "type": "cards",
        "text": _clamp_intro(intro),
        "cards": cards,
        "buttons": [
            {"title": "Tư vấn thêm", "action": "postback", "payload": _slug("Tư vấn thêm")},
            {"title": "Gửi CV", "action": "postback", "payload": _slug("Gửi CV")},
        ],
    }


def _merge_structured(
    display_type: str,
    ai_reply: str,
    products,
    quick_replies,
    llm_text: str,
) -> dict:
    merged = _normalize_structured(
        {
            "display_type": display_type,
            "ai_reply": ai_reply,
            "products": products,
            "quick_replies": quick_replies,
        }
    )
    leaked = _parse_embedded_structured(llm_text)
    if leaked:
        leaked_norm = _normalize_structured(leaked)
        for key in ("display_type", "ai_reply", "products", "quick_replies"):
            if not merged.get(key) and leaked_norm.get(key):
                merged[key] = leaked_norm[key]
        if not merged["ai_reply"]:
            merged["ai_reply"] = _strip_structured_leak(llm_text)
    elif not merged["ai_reply"]:
        merged["ai_reply"] = _strip_structured_leak(llm_text)
    return merged


def main(
    llm_text: str,
    display_type: str = "",
    ai_reply: str = "",
    products=None,
    quick_replies=None,
    hero_image: str = "",
) -> dict:
    merged = _merge_structured(display_type, ai_reply, products, quick_replies, llm_text)
    rich = _build_from_structured(merged, fallback_text=llm_text, hero_image=hero_image)
    if rich:
        return {"reply": json.dumps(rich, ensure_ascii=False)}

    leaked_blob = _parse_embedded_structured(llm_text)
    if leaked_blob:
        rich = _build_from_structured(
            _normalize_structured(leaked_blob),
            fallback_text="",
            hero_image=hero_image,
        )
        if rich:
            return {"reply": json.dumps(rich, ensure_ascii=False)}

    text = _strip_structured_leak(llm_text)
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and parsed.get("type") in {
                "cards", "actions", "quick_replies", "text", "attachment", "template"
            }:
                return {"reply": json.dumps(parsed, ensure_ascii=False)}
            rich = _build_from_structured(parsed, fallback_text="", hero_image=hero_image)
            if rich:
                return {"reply": json.dumps(rich, ensure_ascii=False)}
        except json.JSONDecodeError:
            pass

    job_cards = _build_job_cards_from_text(text)
    if job_cards:
        return {"reply": json.dumps(job_cards, ensure_ascii=False)}

    fallback_intro = text
    if fallback_intro.startswith("{") or '"ai_reply"' in fallback_intro:
        fallback_intro = str(_normalize_structured(leaked_blob or {}).get("ai_reply") or "").strip()

    payload = {
        "type": "actions",
        "text": _clamp_intro(fallback_intro or "Em có thể hỗ trợ gì thêm cho anh/chị ạ?"),
        "buttons": [
            {"title": "Tư vấn thêm", "action": "postback", "payload": _slug("Tư vấn thêm")},
            {"title": "Xem thêm", "action": "postback", "payload": _slug("Xem thêm")},
            {"title": "Liên hệ", "action": "postback", "payload": _slug("Liên hệ")},
        ],
    }
    return {"reply": json.dumps(payload, ensure_ascii=False)}
'''


def code_node_data(
    *,
    llm_node_id: str,
    title: str,
    use_structured_fields: bool = False,
    hero_image_url: str = "",
) -> dict[str, Any]:
    variables: list[dict[str, Any]] = [
        {"variable": "llm_text", "value_selector": [llm_node_id, "text"]},
    ]
    if use_structured_fields:
        variables.extend(
            [
                {
                    "variable": "display_type",
                    "value_selector": [llm_node_id, "structured_output", "display_type"],
                },
                {
                    "variable": "ai_reply",
                    "value_selector": [llm_node_id, "structured_output", "ai_reply"],
                },
                {
                    "variable": "products",
                    "value_selector": [llm_node_id, "structured_output", "products"],
                },
                {
                    "variable": "quick_replies",
                    "value_selector": [llm_node_id, "structured_output", "quick_replies"],
                },
            ]
        )
    code = RICH_REPLY_CODE.strip()
    if hero_image_url:
        hero_literal = json.dumps(hero_image_url, ensure_ascii=False)
        code = code.replace('hero_image: str = "",', f"hero_image: str = {hero_literal},", 1)
    return {
        "type": "code",
        "title": title,
        "desc": "Chuyển output LLM sang JSON rich reply (card/button) cho omnichannel",
        "selected": False,
        "code_language": "python3",
        "code": code,
        "variables": variables,
        "outputs": {"reply": {"type": "string", "children": None}},
    }


def canvas_node(node_id: str, data: dict[str, Any], x: float, y: float, *, width: int = 242, height: int = 54) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": x, "y": y},
        "positionAbsolute": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
        "width": width,
        "height": height,
        "selected": False,
        "data": data,
    }


def edge(source: str, target: str, *, source_type: str, target_type: str) -> dict[str, Any]:
    return {
        "id": f"{source}-source-{target}-target",
        "type": "custom",
        "source": source,
        "sourceHandle": "source",
        "target": target,
        "targetHandle": "target",
        "data": {
            "sourceType": source_type,
            "targetType": target_type,
            "isInIteration": False,
            "isInLoop": False,
        },
        "zIndex": 0,
    }


def find_node(graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def patch_viet_automate(graph: dict[str, Any], cfg: dict[str, Any]) -> int:
    changes = 0
    llm_id = cfg["llm_node_ids"][0]
    code_id = cfg["code_node_id"]
    llm = find_node(graph, llm_id)
    answer = find_node(graph, "answer")
    if not llm or not answer:
        raise ValueError("Viet Automate workflow missing llm or answer node")

    llm_data = llm["data"]
    if cfg.get("enable_structured_output") and not llm_data.get("structured_output_enabled"):
        llm_data["structured_output_enabled"] = True
        changes += 1
    suffix = cfg.get("structured_prompt_suffix") or ""
    if suffix:
        templates = llm_data.get("prompt_template") or []
        if templates:
            prompt_text = templates[0].get("text") or ""
            for marker in ("\n\nKhi gợi ý sản phẩm", "\n\nĐịnh dạng trả lời cho Messenger"):
                idx = prompt_text.find(marker)
                if idx >= 0:
                    prompt_text = prompt_text[:idx]
            prompt_text = prompt_text.replace(
                "trả lời chi tiết dễ hiểu",
                "trả lời gọn 2-4 câu dễ hiểu",
            )
            if suffix not in prompt_text:
                prompt_text = prompt_text.rstrip() + suffix
                templates[0]["text"] = prompt_text
                llm_data["prompt_template"] = templates
                changes += 1

    code = find_node(graph, code_id)
    code_data = code_node_data(
        llm_node_id=llm_id,
        title="Format Rich Reply",
        use_structured_fields=bool(cfg.get("enable_structured_output")),
        hero_image_url=str(cfg.get("hero_image_url") or ""),
    )
    if code is None:
        pos = llm.get("position") or {"x": 1100, "y": 300}
        graph["nodes"].append(
            canvas_node(code_id, code_data, pos["x"] + 260, pos["y"], height=88)
        )
        changes += 1
    else:
        code["data"] = code_data
        changes += 1

    edges = graph.get("edges", [])
    new_edges: list[dict[str, Any]] = []
    for item in edges:
        src, tgt = item.get("source"), item.get("target")
        if src == llm_id and tgt == "answer":
            changes += 1
            continue
        if src == llm_id and tgt == code_id:
            continue
        if src == code_id and tgt == "answer":
            continue
        new_edges.append(item)
    new_edges.append(edge(llm_id, code_id, source_type="llm", target_type="code"))
    new_edges.append(edge(code_id, "answer", source_type="code", target_type="answer"))
    graph["edges"] = new_edges

    if answer["data"].get("answer") != f"{{{{#{code_id}.reply#}}}}":
        answer["data"]["answer"] = f"{{{{#{code_id}.reply#}}}}"
        changes += 1
    return changes


def patch_vieclamtop(graph: dict[str, Any], cfg: dict[str, Any]) -> int:
    changes = 0
    llm_to_answer: dict[str, str] = cfg["llm_to_answer"]
    code_base_id = int(cfg["code_node_id"])

    for index, llm_id in enumerate(cfg["llm_node_ids"]):
        answer_id = llm_to_answer.get(llm_id)
        llm = find_node(graph, llm_id)
        answer = find_node(graph, answer_id) if answer_id else None
        if not llm or not answer:
            continue

        code_id = str(code_base_id + index)
        code_data = code_node_data(
            llm_node_id=llm_id,
            title=f"Rich Reply {llm['data'].get('title', llm_id)}",
            use_structured_fields=False,
        )
        code = find_node(graph, code_id)
        pos = llm.get("position") or {"x": 0, "y": 0}
        if code is None:
            graph["nodes"].append(
                canvas_node(code_id, code_data, pos["x"] + 260, pos["y"], height=88)
            )
            changes += 1
        else:
            code["data"] = code_data
            changes += 1

        edges = graph.get("edges", [])
        new_edges: list[dict[str, Any]] = []
        for item in edges:
            src, tgt = item.get("source"), item.get("target")
            if src == llm_id and tgt == answer_id:
                changes += 1
                continue
            if src == llm_id and tgt == code_id:
                continue
            if src == code_id and tgt == answer_id:
                continue
            new_edges.append(item)
        new_edges.append(edge(llm_id, code_id, source_type="llm", target_type="code"))
        new_edges.append(edge(code_id, answer_id, source_type="code", target_type="answer"))
        graph["edges"] = new_edges

        desired = f"{{{{#{code_id}.reply#}}}}"
        if answer["data"].get("answer") != desired:
            answer["data"]["answer"] = desired
            changes += 1
    return changes


def patch_graph(graph: dict[str, Any], app_id: str, cfg: dict[str, Any]) -> int:
    if app_id == "5556270c-c1e9-4454-9212-f66b281ead51":
        return patch_viet_automate(graph, cfg)
    return patch_vieclamtop(graph, cfg)


def publish_draft(conn, app_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, type, graph, features, environment_variables,
                   conversation_variables, rag_pipeline_variables, created_by
            FROM workflows
            WHERE app_id = %s AND version = 'draft'
            """,
            (app_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            _draft_id,
            tenant_id,
            wf_type,
            graph,
            features,
            environment_variables,
            conversation_variables,
            rag_pipeline_variables,
            created_by,
        ) = row
        new_id = str(uuid.uuid4())
        version = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
        cur.execute(
            """
            INSERT INTO workflows (
                id, tenant_id, app_id, type, version, graph, features,
                environment_variables, conversation_variables, rag_pipeline_variables,
                created_by, updated_by, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                new_id,
                tenant_id,
                app_id,
                wf_type,
                version,
                graph if isinstance(graph, str) else json.dumps(graph, ensure_ascii=False),
                features if isinstance(features, str) else json.dumps(features, ensure_ascii=False),
                environment_variables,
                conversation_variables,
                rag_pipeline_variables,
                created_by,
                created_by,
            ),
        )
        cur.execute("UPDATE apps SET workflow_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_id, app_id))
    return new_id


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        for app_id, cfg in APPS.items():
            wf_id = cfg["draft_workflow_id"]
            with conn.cursor() as cur:
                cur.execute("SELECT graph FROM workflows WHERE id = %s", (wf_id,))
                row = cur.fetchone()
                if not row:
                    print(f"SKIP {app_id}: workflow {wf_id} not found")
                    continue
                graph = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                graph = copy.deepcopy(graph)
                changes = patch_graph(graph, app_id, cfg)
                cur.execute(
                    """
                    UPDATE workflows
                    SET graph = %s::json,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (json.dumps(graph, ensure_ascii=False), wf_id),
                )
            conn.commit()
            published_id = publish_draft(conn, app_id)
            conn.commit()
            print(
                f"OK app={app_id} draft={wf_id} changes={changes} published={published_id or 'FAILED'}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
