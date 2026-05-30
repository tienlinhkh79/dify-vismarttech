"""Fix PJ Store lookup flow: Template merge + Assigner placement."""

from __future__ import annotations

import json
from typing import Any

import psycopg2

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"
PE_LOOKUP = "1776147263725"
IF_LOOKUP_CODE = "177999010001"
KVP_BY_CODE = "177999010002"
KVP_SEARCH = "177999010003"
TMPL_LOOKUP = "1776150090873"
ASSIGN_PRODUCT = "177999010004"
LLM_LOOKUP = "1775471817904"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

TEMPLATE = (
    "{% if json_search and json_search != 'None' and json_search != '' %}"
    "{{ json_search }}"
    "{% elif json_by_code and json_by_code != 'None' and json_by_code != '' %}"
    "{{ json_by_code }}"
    "{% else %}"
    "[]"
    "{% endif %}"
)

TEMPLATE_VARS = [
    {"variable": "json_by_code", "value_selector": [KVP_BY_CODE, "json"]},
    {"variable": "json_search", "value_selector": [KVP_SEARCH, "json"]},
]


def patch_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph["nodes"]
    edges = graph["edges"]

    for node in nodes:
        if node["id"] == TMPL_LOOKUP:
            node["data"]["template"] = TEMPLATE
            node["data"]["variables"] = TEMPLATE_VARS

    # Re-route: PE -> Assigner -> IF (instead of PE -> IF, Template -> Assigner)
    edges = [e for e in edges if not (
        (e["source"] == PE_LOOKUP and e["target"] == IF_LOOKUP_CODE)
        or (e["source"] == TMPL_LOOKUP and e["target"] == ASSIGN_PRODUCT)
        or (e["source"] == ASSIGN_PRODUCT and e["target"] == LLM_LOOKUP)
    )]
    edges.extend([
        {"id": f"{PE_LOOKUP}-source-{ASSIGN_PRODUCT}-target", "type": "custom", "source": PE_LOOKUP, "target": ASSIGN_PRODUCT, "sourceHandle": "source", "targetHandle": "target", "data": {"sourceType": "parameter-extractor", "targetType": "assigner", "isInIteration": False}},
        {"id": f"{ASSIGN_PRODUCT}-source-{IF_LOOKUP_CODE}-target", "type": "custom", "source": ASSIGN_PRODUCT, "target": IF_LOOKUP_CODE, "sourceHandle": "source", "targetHandle": "target", "data": {"sourceType": "assigner", "targetType": "if-else", "isInIteration": False}},
        {"id": f"{TMPL_LOOKUP}-source-{LLM_LOOKUP}-target", "type": "custom", "source": TMPL_LOOKUP, "target": LLM_LOOKUP, "sourceHandle": "source", "targetHandle": "target", "data": {"sourceType": "template-transform", "targetType": "llm", "isInIteration": False}},
    ])
    graph["edges"] = edges
    return graph


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM workflows
                WHERE app_id = %s AND version = 'draft'
                """,
                (APP_ID,),
            )
            draft_row = cur.fetchone()
            if not draft_row:
                raise RuntimeError(f"No draft workflow for app {APP_ID}")
            draft_id = draft_row[0]

            cur.execute(
                """
                SELECT w.id FROM workflows w
                JOIN apps a ON a.workflow_id = w.id
                WHERE a.id = %s
                """,
                (APP_ID,),
            )
            published_row = cur.fetchone()
            target_ids = [draft_id]
            if published_row and published_row[0] != draft_id:
                target_ids.append(published_row[0])

            for workflow_id in target_ids:
                cur.execute("SELECT graph FROM workflows WHERE id = %s", (workflow_id,))
                graph = cur.fetchone()[0]
                if isinstance(graph, str):
                    graph = json.loads(graph)
                graph = patch_graph(graph)
                cur.execute(
                    "UPDATE workflows SET graph = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (json.dumps(graph, ensure_ascii=False), workflow_id),
                )
                print(f"Patched workflow {workflow_id}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
