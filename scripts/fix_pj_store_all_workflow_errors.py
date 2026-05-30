"""Fix all PJ Store workflow validation / branch reference issues."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

import psycopg2

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"

# Node IDs
PE_LOOKUP = "1776147263725"
IF_LOOKUP_CODE = "177999010001"
KVP_BY_CODE = "177999010002"
KVP_SEARCH = "177999010003"
TMPL_LOOKUP = "1776150090873"
ASSIGN_PRODUCT = "177999010004"
LLM_LOOKUP = "1775471817904"

PE_CHOT = "1779987263725"
IF_CHOT_PRODUCT = "177999010026"
IF_CHOT_READY = "177999010005"

PE_SUPPLEMENT = "177999014001"
ASSIGN_CUSTOMER = "177999014002"
IF_SUPPLEMENT_READY = "177999014003"

ASSIGN_CHOT = "177999014006"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

CONV_VARS = {
    "product_code": {
        "id": "0f3c5350-4216-455c-a401-4d83dd830a4f",
        "name": "product_code",
        "value_type": "string",
        "value": "",
        "description": "Mã sản phẩm đang quan tâm",
        "selector": ["conversation", "product_code"],
    },
    "product_name": {
        "id": "17e78d47-b54d-42e2-9f56-f7c20ea8e799",
        "name": "product_name",
        "value_type": "string",
        "value": "",
        "description": "Tên sản phẩm đang quan tâm",
        "selector": ["conversation", "product_name"],
    },
    "customer_name": {
        "id": "c19af338-c2a5-4d71-bdea-685ad2d7a5e5",
        "name": "customer_name",
        "value_type": "string",
        "value": "",
        "description": "Họ tên người nhận",
        "selector": ["conversation", "customer_name"],
    },
    "customer_phone": {
        "id": "ec9c6e57-18c7-4268-9481-6207b86dd338",
        "name": "customer_phone",
        "value_type": "string",
        "value": "",
        "description": "SĐT người nhận",
        "selector": ["conversation", "customer_phone"],
    },
    "customer_address": {
        "id": "718eef83-3750-49bb-a554-ac7401897f2e",
        "name": "customer_address",
        "value_type": "string",
        "value": "",
        "description": "Địa chỉ giao hàng",
        "selector": ["conversation", "customer_address"],
    },
}

LOOKUP_TEMPLATE = (
    "{% if json_search and json_search != 'None' and json_search != '' %}"
    "{{ json_search }}"
    "{% elif json_by_code and json_by_code != 'None' and json_by_code != '' %}"
    "{{ json_by_code }}"
    "{% else %}"
    "[]"
    "{% endif %}"
)

LOOKUP_TEMPLATE_VARS = [
    {"variable": "json_by_code", "value_selector": [KVP_BY_CODE, "json"]},
    {"variable": "json_search", "value_selector": [KVP_SEARCH, "json"]},
]


def edge(source: str, target: str, source_handle: str = "source") -> dict[str, Any]:
    source_type_map = {
        PE_LOOKUP: "parameter-extractor",
        PE_CHOT: "parameter-extractor",
        PE_SUPPLEMENT: "parameter-extractor",
        ASSIGN_PRODUCT: "assigner",
        ASSIGN_CUSTOMER: "assigner",
        ASSIGN_CHOT: "assigner",
        IF_LOOKUP_CODE: "if-else",
        IF_CHOT_PRODUCT: "if-else",
        IF_SUPPLEMENT_READY: "if-else",
        TMPL_LOOKUP: "template-transform",
        KVP_BY_CODE: "tool",
        KVP_SEARCH: "tool",
    }
    target_type_map = {
        ASSIGN_PRODUCT: "assigner",
        ASSIGN_CUSTOMER: "assigner",
        ASSIGN_CHOT: "assigner",
        IF_LOOKUP_CODE: "if-else",
        IF_CHOT_PRODUCT: "if-else",
        IF_SUPPLEMENT_READY: "if-else",
        TMPL_LOOKUP: "template-transform",
        LLM_LOOKUP: "llm",
        KVP_BY_CODE: "tool",
        KVP_SEARCH: "tool",
    }
    return {
        "id": f"{source}-{source_handle}-{target}",
        "type": "custom",
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": "target",
        "zIndex": 0,
        "data": {
            "isInIteration": False,
            "isInLoop": False,
            "sourceType": source_type_map.get(source, "custom"),
            "targetType": target_type_map.get(target, "custom"),
        },
    }


def assign_item(conv_key: str, value_selector: list[str]) -> dict[str, Any]:
    return {
        "variable_selector": ["conversation", conv_key],
        "input_type": "variable",
        "operation": "over-write",
        "value": value_selector,
    }


def assigner_node(node_id: str, title: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": 0, "y": 0},
        "positionAbsolute": {"x": 0, "y": 0},
        "targetPosition": "left",
        "sourcePosition": "right",
        "width": 242,
        "height": 86,
        "selected": False,
        "data": {
            "type": "assigner",
            "title": title,
            "desc": "",
            "selected": False,
            "version": "2",
            "items": items,
        },
    }


def if_condition(variable_selector: list[str], operator: str = "not empty") -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "varType": "string",
        "variable_selector": variable_selector,
        "comparison_operator": operator,
        "value": "",
    }


def patch_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_by_id = {n["id"]: n for n in nodes}

    # 1) Lookup template reads both KiotViet branches
    if TMPL_LOOKUP in node_by_id:
        node_by_id[TMPL_LOOKUP]["data"]["template"] = LOOKUP_TEMPLATE
        node_by_id[TMPL_LOOKUP]["data"]["variables"] = LOOKUP_TEMPLATE_VARS

    # 2) Ensure lookup assigner items correct
    if ASSIGN_PRODUCT in node_by_id:
        node_by_id[ASSIGN_PRODUCT]["data"]["items"] = [
            assign_item("product_code", [PE_LOOKUP, "product_code"]),
            assign_item("product_name", [PE_LOOKUP, "product_name"]),
        ]
        node_by_id[ASSIGN_PRODUCT]["data"]["version"] = "2"

    # 3) Ensure supplement assigner items correct
    if ASSIGN_CUSTOMER in node_by_id:
        node_by_id[ASSIGN_CUSTOMER]["data"]["items"] = [
            assign_item("customer_name", [PE_SUPPLEMENT, "customer_name"]),
            assign_item("customer_phone", [PE_SUPPLEMENT, "customer_phone"]),
            assign_item("customer_address", [PE_SUPPLEMENT, "customer_address"]),
        ]
        node_by_id[ASSIGN_CUSTOMER]["data"]["version"] = "2"

    # 4) Supplement IF: check PE output directly (same branch, no false invalid refs)
    if IF_SUPPLEMENT_READY in node_by_id:
        node_by_id[IF_SUPPLEMENT_READY]["data"]["cases"] = [{
            "id": "true",
            "case_id": "true",
            "logical_operator": "and",
            "conditions": [
                if_condition(["conversation", "product_code"]),
                if_condition([PE_SUPPLEMENT, "customer_phone"]),
                if_condition([PE_SUPPLEMENT, "customer_name"]),
                if_condition([PE_SUPPLEMENT, "customer_address"]),
            ],
        }]

    # 5) Add / update chốt assigner right after PE Chốt
    chot_items = [
        assign_item("product_code", [PE_CHOT, "product_code"]),
        assign_item("product_name", [PE_CHOT, "product_name"]),
        assign_item("customer_name", [PE_CHOT, "customer_name"]),
        assign_item("customer_phone", [PE_CHOT, "customer_phone"]),
        assign_item("customer_address", [PE_CHOT, "customer_address"]),
    ]
    if ASSIGN_CHOT in node_by_id:
        node_by_id[ASSIGN_CHOT]["data"]["items"] = chot_items
        node_by_id[ASSIGN_CHOT]["data"]["version"] = "2"
    else:
        pe_chot_node = node_by_id[PE_CHOT]
        pos = pe_chot_node.get("position", {"x": 900, "y": 780})
        new_node = assigner_node(ASSIGN_CHOT, "Lưu thông tin chốt", chot_items)
        new_node["position"] = {"x": pos["x"] + 220, "y": pos["y"]}
        new_node["positionAbsolute"] = copy.deepcopy(new_node["position"])
        nodes.append(new_node)
        node_by_id[ASSIGN_CHOT] = new_node

    # 6) Chốt IF ready: prefer conversation vars saved by assigner
    if IF_CHOT_READY in node_by_id:
        node_by_id[IF_CHOT_READY]["data"]["cases"] = [{
            "id": "true",
            "case_id": "true",
            "logical_operator": "and",
            "conditions": [
                if_condition(["conversation", "customer_phone"]),
                if_condition(["conversation", "customer_name"]),
                if_condition(["conversation", "customer_address"]),
            ],
        }]

    # 7) Rewire edges for branch-safe assigner placement
    remove_pairs = {
        (PE_LOOKUP, IF_LOOKUP_CODE),
        (TMPL_LOOKUP, ASSIGN_PRODUCT),
        (ASSIGN_PRODUCT, LLM_LOOKUP),
        (PE_CHOT, IF_CHOT_PRODUCT),
    }
    edges = [
        e for e in edges
        if (e["source"], e["target"]) not in remove_pairs
    ]

    new_edges = [
        edge(PE_LOOKUP, ASSIGN_PRODUCT),
        edge(ASSIGN_PRODUCT, IF_LOOKUP_CODE),
        edge(TMPL_LOOKUP, LLM_LOOKUP),
        edge(PE_CHOT, ASSIGN_CHOT),
        edge(ASSIGN_CHOT, IF_CHOT_PRODUCT),
    ]
    existing_ids = {e["id"] for e in edges}
    for new_edge in new_edges:
        if new_edge["id"] not in existing_ids:
            edges.append(new_edge)

    graph["nodes"] = nodes
    graph["edges"] = edges
    return graph


def target_workflow_ids(cur) -> list[str]:
    cur.execute(
        "SELECT id FROM workflows WHERE app_id = %s AND version = 'draft'",
        (APP_ID,),
    )
    draft_id = cur.fetchone()[0]
    cur.execute(
        """
        SELECT w.id FROM workflows w
        JOIN apps a ON a.workflow_id = w.id
        WHERE a.id = %s
        """,
        (APP_ID,),
    )
    row = cur.fetchone()
    ids = [draft_id]
    if row and row[0] != draft_id:
        ids.append(row[0])
    return ids


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor() as cur:
            for workflow_id in target_workflow_ids(cur):
                cur.execute("SELECT graph FROM workflows WHERE id = %s", (workflow_id,))
                graph = cur.fetchone()[0]
                if isinstance(graph, str):
                    graph = json.loads(graph)
                graph = patch_graph(graph)
                cur.execute(
                    """
                    UPDATE workflows
                    SET graph = %s,
                        conversation_variables = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        json.dumps(graph, ensure_ascii=False),
                        json.dumps(CONV_VARS, ensure_ascii=False),
                        workflow_id,
                    ),
                )
                print(f"Patched workflow {workflow_id}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
