"""Fix PJ Store checkout flow to accept product name and remembered context."""

from __future__ import annotations

import json
from typing import Any

import psycopg2

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"
ACTIVE_WORKFLOW_ID = "de014de1-7302-45e7-9177-bc231de78ff1"
DRAFT_WORKFLOW_ID = "e46ef02f-e392-4e41-870c-040add152a1f"

CHECK_HAS_PRODUCT_ID = "177999010026"
RESOLVE_PRODUCT_ID = "177999010033"
LOOKUP_PRODUCT_ID = "177999010007"
CHECKOUT_EXTRACT_ID = "1779987263725"
SAVE_CHECKOUT_INFO_ID = "177999014006"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}


def _decode_graph(raw_graph: Any) -> dict[str, Any]:
    if isinstance(raw_graph, str):
        return json.loads(raw_graph)
    return raw_graph


def _find_node(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in graph["nodes"]:
        if node["id"] == node_id:
            return node
    raise RuntimeError(f"Node {node_id} not found")


def _upsert_condition(conditions: list[dict[str, Any]], selector: list[str], condition_id: str) -> None:
    for condition in conditions:
        if condition.get("variable_selector") == selector:
            condition["id"] = condition_id
            return
    conditions.append(
        {
            "id": condition_id,
            "varType": "string",
            "variable_selector": selector,
            "comparison_operator": "not empty",
            "value": "",
        }
    )


def transform_graph(graph: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(graph))

    # 1) Allow checkout flow to continue when only product_name is known.
    check_product_node = _find_node(updated, CHECK_HAS_PRODUCT_ID)
    true_case = check_product_node["data"]["cases"][0]
    conditions = true_case["conditions"]
    _upsert_condition(conditions, [CHECKOUT_EXTRACT_ID, "product_name"], "fix-checkout-extracted-product-name")
    _upsert_condition(conditions, ["conversation", "product_name"], "fix-checkout-conversation-product-name")

    # Strengthen extractor behavior for implicit "chốt luôn/món này" messages.
    extractor_node = _find_node(updated, CHECKOUT_EXTRACT_ID)
    extractor_node["data"]["instruction"] = (
        "Khách đang chốt/đặt mua. Extract từ tin nhắn + toàn bộ ngữ cảnh chat gần đây:\n"
        "- product_code: ưu tiên mã trong tin nhắn; nếu không có thì lấy mã SP vừa được nhắc gần nhất.\n"
        "- product_name: nếu user nói 'món này/chốt luôn/lấy cái đó' thì lấy tên SP gần nhất trong hội thoại.\n"
        "- quantity (mặc định 1), customer_name, customer_phone, customer_address.\n"
        "Không bịa thông tin."
    )
    extractor_node["data"]["memory"] = {
        "role_prefix": {"assistant": "", "user": ""},
        "window": {"enabled": True, "size": 12},
    }

    # 2) Resolve lookup action dynamically:
    # - if has product_code -> get_by_code
    # - else if has product_name -> search
    resolve_node = _find_node(updated, RESOLVE_PRODUCT_ID)
    resolve_node["data"]["variables"] = [
        {"variable": "product_code", "value_selector": [CHECKOUT_EXTRACT_ID, "product_code"]},
        {"variable": "conv_product_code", "value_selector": ["conversation", "product_code"]},
        {"variable": "product_name", "value_selector": [CHECKOUT_EXTRACT_ID, "product_name"]},
        {"variable": "conv_product_name", "value_selector": ["conversation", "product_name"]},
    ]
    resolve_node["data"]["code"] = (
        "def main(product_code: str, conv_product_code: str, product_name: str, conv_product_name: str) -> dict:\n"
        "    code = (product_code or conv_product_code or \"\").strip()\n"
        "    name = (product_name or conv_product_name or \"\").strip()\n"
        "    action = \"get_by_code\" if code else (\"search\" if name else \"get_by_code\")\n"
        "    return {\n"
        "        \"lookup_action\": action,\n"
        "        \"lookup_code\": code,\n"
        "        \"lookup_name\": name,\n"
        "    }\n"
    )
    resolve_node["data"]["outputs"] = {
        "lookup_action": {"type": "string", "children": None},
        "lookup_code": {"type": "string", "children": None},
        "lookup_name": {"type": "string", "children": None},
    }

    # 3) Bind lookup tool to dynamic action/code/name from resolver.
    lookup_node = _find_node(updated, LOOKUP_PRODUCT_ID)
    lookup_node["data"]["tool_parameters"]["action"] = {"type": "mixed", "value": "{{#177999010033.lookup_action#}}"}
    lookup_node["data"]["tool_parameters"]["code"] = {"type": "mixed", "value": "{{#177999010033.lookup_code#}}"}
    lookup_node["data"]["tool_parameters"]["name"] = {"type": "mixed", "value": "{{#177999010033.lookup_name#}}"}

    # Keep conversation memory updated from resolved values (never from potentially empty raw extract).
    save_node = _find_node(updated, SAVE_CHECKOUT_INFO_ID)
    save_node["data"]["items"] = [
        {
            "variable_selector": ["conversation", "product_code"],
            "input_type": "variable",
            "operation": "over-write",
            "value": [RESOLVE_PRODUCT_ID, "lookup_code"],
        },
        {
            "variable_selector": ["conversation", "product_name"],
            "input_type": "variable",
            "operation": "over-write",
            "value": [RESOLVE_PRODUCT_ID, "lookup_name"],
        },
    ]

    # 4) Rewire flow:
    # - check product before save (avoid early overwrite)
    # - on true branch: Resolve -> Save -> Lookup
    edges: list[dict[str, Any]] = updated["edges"]
    edges = [
        edge
        for edge in edges
        if not (
            (edge.get("source") == CHECKOUT_EXTRACT_ID and edge.get("target") == SAVE_CHECKOUT_INFO_ID)
            or (edge.get("source") == SAVE_CHECKOUT_INFO_ID and edge.get("target") == CHECK_HAS_PRODUCT_ID)
            or (edge.get("source") == RESOLVE_PRODUCT_ID and edge.get("target") == LOOKUP_PRODUCT_ID)
        )
    ]
    direct_exists = any(
        edge.get("source") == CHECKOUT_EXTRACT_ID and edge.get("target") == CHECK_HAS_PRODUCT_ID for edge in edges
    )
    if not direct_exists:
        edges.append(
            {
                "id": f"{CHECKOUT_EXTRACT_ID}-source-{CHECK_HAS_PRODUCT_ID}",
                "type": "custom",
                "source": CHECKOUT_EXTRACT_ID,
                "target": CHECK_HAS_PRODUCT_ID,
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"isInIteration": False, "isInLoop": False},
                "zIndex": 0,
            }
        )

    resolve_to_save_exists = any(
        edge.get("source") == RESOLVE_PRODUCT_ID and edge.get("target") == SAVE_CHECKOUT_INFO_ID for edge in edges
    )
    if not resolve_to_save_exists:
        edges.append(
            {
                "id": f"{RESOLVE_PRODUCT_ID}-source-{SAVE_CHECKOUT_INFO_ID}",
                "type": "custom",
                "source": RESOLVE_PRODUCT_ID,
                "target": SAVE_CHECKOUT_INFO_ID,
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"isInIteration": False, "isInLoop": False},
                "zIndex": 0,
            }
        )

    save_to_lookup_exists = any(
        edge.get("source") == SAVE_CHECKOUT_INFO_ID and edge.get("target") == LOOKUP_PRODUCT_ID for edge in edges
    )
    if not save_to_lookup_exists:
        edges.append(
            {
                "id": f"{SAVE_CHECKOUT_INFO_ID}-source-{LOOKUP_PRODUCT_ID}",
                "type": "custom",
                "source": SAVE_CHECKOUT_INFO_ID,
                "target": LOOKUP_PRODUCT_ID,
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"isInIteration": False, "isInLoop": False},
                "zIndex": 0,
            }
        )
    updated["edges"] = edges

    return updated


def load_graph(conn: psycopg2.extensions.connection, workflow_id: str) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT graph FROM workflows WHERE id = %s", (workflow_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Workflow {workflow_id} not found")
        return _decode_graph(row[0])


def save_graph(conn: psycopg2.extensions.connection, workflow_id: str, graph: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE workflows
            SET graph = %s::json,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (json.dumps(graph, ensure_ascii=False), workflow_id),
        )
    conn.commit()


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        for workflow_id in (ACTIVE_WORKFLOW_ID, DRAFT_WORKFLOW_ID):
            graph = load_graph(conn, workflow_id)
            updated = transform_graph(graph)
            save_graph(conn, workflow_id, updated)
            print(f"OK {workflow_id}: nodes={len(updated['nodes'])}, edges={len(updated['edges'])}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
