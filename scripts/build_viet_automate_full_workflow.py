"""Build full PJ Store-style workflow for Trợ lý AI Việt Automate.

Adds Question Classifier, greet/thanks answers, lead capture (Parameter Extractor
+ IF/ELSE + Mini CRM update_crm_lead), and keeps KB → LLM → Format Rich Reply → Answer
for the main FAQ branch.

Run inside docker-api-1:
  docker cp scripts/build_viet_automate_full_workflow.py docker-api-1:/tmp/
  docker exec docker-api-1 bash -lc "/app/api/.venv/bin/python /tmp/build_viet_automate_full_workflow.py"
"""

from __future__ import annotations

import copy
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg2

# Allow importing patch helpers from sibling script when copied to /tmp alone.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from add_omnichannel_rich_reply_nodes import APPS, patch_viet_automate, publish_draft  # noqa: E402

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

APP_ID = "5556270c-c1e9-4454-9212-f66b281ead51"
DRAFT_WORKFLOW_ID = APPS[APP_ID]["draft_workflow_id"]

# Node IDs (stable for Studio links / patches)
START_ID = "1776072202913"
KB_ID = "1780706617058"
LLM_ID = "llm"
CODE_ID = "178200001001"
ANSWER_MAIN_ID = "answer"

CLASSIFIER_ID = "178300001001"
CLS_FAQ_ID = "178300001002"
CLS_GREET_ID = "178300001003"
CLS_THANKS_ID = "178300001004"
CLS_LEAD_ID = "178300001005"

ANSWER_GREET_ID = "178300002001"
ANSWER_THANKS_ID = "178300002002"
ANSWER_NEED_INFO_ID = "178300002003"
ANSWER_LEAD_ID = "178300002004"

LEAD_EXTRACT_ID = "178300003001"
LEAD_IF_PHONE_ID = "178300003002"
CRM_TOOL_ID = "178300003003"
LLM_LEAD_ID = "178300003004"

DEFAULT_MODEL: dict[str, Any] = {
    "completion_params": {"temperature": 0.3, "max_tokens": 256},
    "mode": "chat",
    "name": "cx/gpt-5.4-mini",
    "provider": "langgenius/openai_api_compatible/openai_api_compatible",
}

EXTRACTOR_MODEL: dict[str, Any] = {
    "completion_params": {"temperature": 0.7},
    "mode": "chat",
    "name": "cx/gpt-5.4-mini",
    "provider": "langgenius/openai_api_compatible/openai_api_compatible",
}

CONVERSATION_VARIABLES: dict[str, Any] = {
    "customer_name": {
        "value_type": "string",
        "value": "",
        "id": str(uuid.uuid4()),
        "name": "customer_name",
        "description": "Họ tên khách hàng",
        "selector": ["conversation", "customer_name"],
    },
    "customer_phone": {
        "value_type": "string",
        "value": "",
        "id": str(uuid.uuid4()),
        "name": "customer_phone",
        "description": "Số điện thoại khách",
        "selector": ["conversation", "customer_phone"],
    },
    "service_interest": {
        "value_type": "string",
        "value": "",
        "id": str(uuid.uuid4()),
        "name": "service_interest",
        "description": "Dịch vụ / gói website khách quan tâm",
        "selector": ["conversation", "service_interest"],
    },
}


def canvas_node(
    node_id: str,
    data: dict[str, Any],
    x: float,
    y: float,
    *,
    width: int = 242,
    height: int = 54,
) -> dict[str, Any]:
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


def edge(
    source: str,
    target: str,
    *,
    source_type: str,
    target_type: str,
    source_handle: str = "source",
) -> dict[str, Any]:
    return {
        "id": f"{source}-{source_handle}-{target}-target",
        "type": "custom",
        "source": source,
        "sourceHandle": source_handle,
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


def if_else_node(
    node_id: str,
    title: str,
    variable_selector: list[str],
    *,
    x: float,
    y: float,
) -> dict[str, Any]:
    return canvas_node(
        node_id,
        {
            "type": "if-else",
            "title": title,
            "desc": "",
            "selected": False,
            "cases": [
                {
                    "id": "true",
                    "case_id": "true",
                    "logical_operator": "and",
                    "conditions": [
                        {
                            "id": str(uuid.uuid4()),
                            "varType": "string",
                            "variable_selector": variable_selector,
                            "comparison_operator": "not empty",
                            "value": "",
                        }
                    ],
                }
            ],
            "isInIteration": False,
            "isInLoop": False,
        },
        x,
        y,
        height=124,
    )


def find_node(graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def keep_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    keep_ids = {
        START_ID,
        KB_ID,
        LLM_ID,
        CODE_ID,
        ANSWER_MAIN_ID,
        "1776072886890",
        "1776073032757",
        "1776665049022",
    }
    return [n for n in graph.get("nodes", []) if n.get("id") in keep_ids]


def build_full_graph(base_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = keep_nodes(base_graph)
    llm_node = find_node(base_graph, LLM_ID)
    if not llm_node:
        raise ValueError("Missing LLM node in Viet Automate workflow")

    model = copy.deepcopy(llm_node["data"].get("model") or DEFAULT_MODEL)

    classifier = canvas_node(
        CLASSIFIER_ID,
        {
            "type": "question-classifier",
            "title": "Question Classifier",
            "desc": "Phân loại ý định khách hàng Việt Automate",
            "selected": False,
            "classes": [
                {
                    "id": CLS_FAQ_ID,
                    "name": (
                        "Tư vấn dịch vụ, giá, mẫu website, quy trình, thông tin công ty, FAQ. "
                        "Bao gồm nút: Tư vấn mô hình, Xem quy trình, xem_quy_trinh."
                    ),
                },
                {
                    "id": CLS_GREET_ID,
                    "name": "Chào hỏi, xin chào, hello, hi, bắt đầu trò chuyện",
                },
                {
                    "id": CLS_THANKS_ID,
                    "name": "Cảm ơn, tạm biệt, bye, thanks, kết thúc",
                },
                {
                    "id": CLS_LEAD_ID,
                    "name": (
                        "Liên hệ, đặt thiết kế, nhận tư vấn, báo giá, để lại SĐT/email, "
                        "muốn làm website. Bao gồm nút: Liên hệ, lien_he, nhan_tu_van."
                    ),
                },
            ],
            "query_variable_selector": [START_ID, "sys.query"],
            "instructions": (
                "Phân loại tin nhắn khách (kể cả payload nút bấm/slug). "
                "Ưu tiên lead nếu khách muốn liên hệ hoặc để thông tin."
            ),
            "topics": [],
            "model": model,
            "memory": {
                "role_prefix": {"assistant": "", "user": ""},
                "window": {"enabled": False, "size": 50},
            },
            "vision": {"enabled": False},
        },
        342,
        280,
        height=320,
    )

    answer_greet = canvas_node(
        ANSWER_GREET_ID,
        {
            "type": "answer",
            "title": "Answer Chào",
            "desc": "",
            "selected": False,
            "answer": (
                "Dạ chào anh/chị! Em là trợ lý AI của **Việt Automate** ạ. "
                "Em có thể tư vấn dịch vụ thiết kế website, báo giá và quy trình triển khai. "
                "Anh/chị muốn xem mẫu website, quy trình hay nhận tư vấn trực tiếp ạ?"
            ),
            "variables": [],
        },
        980,
        40,
        height=144,
    )

    answer_thanks = canvas_node(
        ANSWER_THANKS_ID,
        {
            "type": "answer",
            "title": "Answer Cảm ơn",
            "desc": "",
            "selected": False,
            "answer": (
                "Dạ em cảm ơn anh/chị ạ! Cần tư vấn thêm về website hay dịch vụ Việt Automate "
                "cứ nhắn em, em hỗ trợ ngay nha."
            ),
            "variables": [],
        },
        980,
        200,
        height=144,
    )

    lead_extract = canvas_node(
        LEAD_EXTRACT_ID,
        {
            "type": "parameter-extractor",
            "title": "Extract Lead",
            "desc": "",
            "selected": False,
            "query": ["sys", "query"],
            "reasoning_mode": "prompt",
            "model": EXTRACTOR_MODEL,
            "vision": {"enabled": False},
            "instruction": (
                "Khách muốn liên hệ / đặt thiết kế / nhận tư vấn. "
                "Extract từ tin nhắn và ngữ cảnh gần đây:\n"
                "- customer_name: họ tên nếu có\n"
                "- customer_phone: SĐT (10-11 số)\n"
                "- customer_email: email nếu có\n"
                "- service_interest: gói/dịch vụ website khách quan tâm\n"
                "Không bịa thông tin không có trong hội thoại."
            ),
            "parameters": [
                {
                    "name": "customer_name",
                    "type": "string",
                    "required": False,
                    "description": "Họ tên khách hàng",
                },
                {
                    "name": "customer_phone",
                    "type": "string",
                    "required": False,
                    "description": "Số điện thoại liên hệ",
                },
                {
                    "name": "customer_email",
                    "type": "string",
                    "required": False,
                    "description": "Email liên hệ",
                },
                {
                    "name": "service_interest",
                    "type": "string",
                    "required": False,
                    "description": "Dịch vụ / gói website quan tâm",
                },
            ],
            "memory": {
                "role_prefix": {"assistant": "", "user": ""},
                "window": {"enabled": True, "size": 8},
            },
        },
        680,
        520,
        height=88,
    )

    lead_if = if_else_node(
        LEAD_IF_PHONE_ID,
        "Có SĐT?",
        [LEAD_EXTRACT_ID, "customer_phone"],
        x=980,
        y=520,
    )

    crm_tool = canvas_node(
        CRM_TOOL_ID,
        {
            "type": "tool",
            "title": "Lưu CRM Lead",
            "desc": "",
            "selected": False,
            "provider_id": "mini_crm",
            "provider_type": "builtin",
            "provider_name": "mini_crm",
            "tool_name": "update_crm_lead",
            "tool_label": "Save CRM Lead",
            "tool_node_version": "2",
            "tool_configurations": {},
            "tool_parameters": {
                "stage": {"type": "constant", "value": "qualified"},
                "contact_phone": {
                    "type": "mixed",
                    "value": f"{{{{#{LEAD_EXTRACT_ID}.customer_phone#}}}}",
                },
                "contact_email": {
                    "type": "mixed",
                    "value": f"{{{{#{LEAD_EXTRACT_ID}.customer_email#}}}}",
                },
                "tags": {"type": "constant", "value": "Việt Automate,Chatbot"},
                "notes_append": {
                    "type": "mixed",
                    "value": (
                        "Lead từ chatbot — {{#sys.query#}} | "
                        f"Dịch vụ: {{{{#{LEAD_EXTRACT_ID}.service_interest#}}}} | "
                        f"Tên: {{{{#{LEAD_EXTRACT_ID}.customer_name#}}}}"
                    ),
                },
            },
            "params": {},
            "paramSchemas": [],
            "is_team_authorization": True,
            "plugin_id": None,
            "plugin_unique_identifier": "",
            "provider_icon": "/console/api/workspaces/current/tool-provider/builtin/mini_crm/icon",
        },
        1280,
        480,
        height=88,
    )

    llm_lead = canvas_node(
        LLM_LEAD_ID,
        {
            "type": "llm",
            "title": "LLM Xác nhận Lead",
            "desc": "",
            "selected": False,
            "model": EXTRACTOR_MODEL,
            "prompt_template": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "system",
                    "text": (
                        "Bạn là trợ lý Việt Automate. Khách vừa để thông tin liên hệ.\n"
                        f"Tên: {{{{#{LEAD_EXTRACT_ID}.customer_name#}}}}\n"
                        f"SĐT: {{{{#{LEAD_EXTRACT_ID}.customer_phone#}}}}\n"
                        f"Email: {{{{#{LEAD_EXTRACT_ID}.customer_email#}}}}\n"
                        f"Dịch vụ quan tâm: {{{{#{LEAD_EXTRACT_ID}.service_interest#}}}}\n"
                        "CRM đã lưu lead. Trả lời 2-3 câu: cảm ơn, xác nhận đã ghi nhận, "
                        "hẹn team liên hệ sớm. Giọng lịch sự, thân thiện."
                    ),
                    "edition_type": "basic",
                }
            ],
            "context": {"enabled": False, "variable_selector": []},
            "memory": {
                "query_prompt_template": "{{#sys.query#}}",
                "role_prefix": {"assistant": "", "user": ""},
                "window": {"enabled": False, "size": 10},
            },
            "vision": {"enabled": False},
            "structured_output_enabled": False,
            "prompt_config": {"jinja2_variables": []},
        },
        1580,
        480,
        height=146,
    )

    answer_need_info = canvas_node(
        ANSWER_NEED_INFO_ID,
        {
            "type": "answer",
            "title": "Answer Cần SĐT",
            "desc": "",
            "selected": False,
            "answer": (
                "Dạ để team Việt Automate tư vấn chi tiết, anh/chị vui lòng để lại **họ tên** "
                "và **số điện thoại** (hoặc email) ạ. Em sẽ chuyển ngay cho bộ phận tư vấn!"
            ),
            "variables": [],
        },
        1280,
        640,
        height=144,
    )

    answer_lead = canvas_node(
        ANSWER_LEAD_ID,
        {
            "type": "answer",
            "title": "Answer Lead",
            "desc": "",
            "selected": False,
            "answer": f"{{{{#{LLM_LEAD_ID}.text#}}}}",
            "variables": [],
        },
        1880,
        480,
        height=144,
    )

    # Reposition main path nodes for cleaner canvas
    for node in nodes:
        nid = node["id"]
        if nid == START_ID:
            node["position"] = node["positionAbsolute"] = {"x": 0, "y": 280}
        elif nid == KB_ID:
            node["position"] = node["positionAbsolute"] = {"x": 680, "y": 280}
        elif nid == LLM_ID:
            node["position"] = node["positionAbsolute"] = {"x": 980, "y": 280}
        elif nid == CODE_ID:
            node["position"] = node["positionAbsolute"] = {"x": 1280, "y": 280}
        elif nid == ANSWER_MAIN_ID:
            node["position"] = node["positionAbsolute"] = {"x": 1580, "y": 280}

    nodes.extend(
        [
            classifier,
            answer_greet,
            answer_thanks,
            lead_extract,
            lead_if,
            crm_tool,
            llm_lead,
            answer_need_info,
            answer_lead,
        ]
    )

    edges = [
        edge(START_ID, CLASSIFIER_ID, source_type="start", target_type="question-classifier"),
        edge(
            CLASSIFIER_ID,
            KB_ID,
            source_type="question-classifier",
            target_type="knowledge-retrieval",
            source_handle=CLS_FAQ_ID,
        ),
        edge(
            CLASSIFIER_ID,
            ANSWER_GREET_ID,
            source_type="question-classifier",
            target_type="answer",
            source_handle=CLS_GREET_ID,
        ),
        edge(
            CLASSIFIER_ID,
            ANSWER_THANKS_ID,
            source_type="question-classifier",
            target_type="answer",
            source_handle=CLS_THANKS_ID,
        ),
        edge(
            CLASSIFIER_ID,
            LEAD_EXTRACT_ID,
            source_type="question-classifier",
            target_type="parameter-extractor",
            source_handle=CLS_LEAD_ID,
        ),
        edge(KB_ID, LLM_ID, source_type="knowledge-retrieval", target_type="llm"),
        edge(LLM_ID, CODE_ID, source_type="llm", target_type="code"),
        edge(CODE_ID, ANSWER_MAIN_ID, source_type="code", target_type="answer"),
        edge(
            LEAD_EXTRACT_ID,
            LEAD_IF_PHONE_ID,
            source_type="parameter-extractor",
            target_type="if-else",
        ),
        edge(
            LEAD_IF_PHONE_ID,
            CRM_TOOL_ID,
            source_type="if-else",
            target_type="tool",
            source_handle="true",
        ),
        edge(
            LEAD_IF_PHONE_ID,
            ANSWER_NEED_INFO_ID,
            source_type="if-else",
            target_type="answer",
            source_handle="false",
        ),
        edge(CRM_TOOL_ID, LLM_LEAD_ID, source_type="tool", target_type="llm"),
        edge(LLM_LEAD_ID, ANSWER_LEAD_ID, source_type="llm", target_type="answer"),
    ]

    viewport = base_graph.get("viewport") or {"x": -54, "y": 154, "zoom": 0.45}
    return {"nodes": nodes, "edges": edges, "viewport": viewport}


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT graph FROM workflows WHERE id = %s", (DRAFT_WORKFLOW_ID,))
            row = cur.fetchone()
            if not row:
                raise SystemExit(f"Draft workflow {DRAFT_WORKFLOW_ID} not found")

            base = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            graph = build_full_graph(copy.deepcopy(base))
            cfg = APPS[APP_ID]
            patch_changes = patch_viet_automate(graph, cfg)

            cur.execute(
                """
                UPDATE workflows
                SET graph = %s::json,
                    conversation_variables = %s::json,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    json.dumps(graph, ensure_ascii=False),
                    json.dumps(CONVERSATION_VARIABLES, ensure_ascii=False),
                    DRAFT_WORKFLOW_ID,
                ),
            )
        conn.commit()

        published_id = publish_draft(conn, APP_ID)
        conn.commit()
        print(
            f"OK app={APP_ID} draft={DRAFT_WORKFLOW_ID} "
            f"patch_changes={patch_changes} nodes={len(graph['nodes'])} "
            f"edges={len(graph['edges'])} published={published_id or 'FAILED'}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
