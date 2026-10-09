"""Fix Viet Automate workflow Studio loading issues.

- Remove heavy default sticky-note nodes
- Fix malformed variable refs in CRM tool + lead LLM
- Enrich mini_crm tool node metadata (tool_description, paramSchemas)
"""

from __future__ import annotations

import copy
import json
import sys
import uuid
from pathlib import Path

import psycopg2

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from add_omnichannel_rich_reply_nodes import APPS, publish_draft  # noqa: E402

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

APP_ID = "5556270c-c1e9-4454-9212-f66b281ead51"
DRAFT_ID = APPS[APP_ID]["draft_workflow_id"]
LEAD_EXTRACT_ID = "178300003001"
CRM_TOOL_ID = "178300003003"
LLM_LEAD_ID = "178300003004"

NOTE_IDS = {"1776072886890", "1776073032757", "1776665049022"}


def find_node(graph: dict, node_id: str) -> dict | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def fix_graph(graph: dict) -> int:
    changes = 0
    nodes = graph.get("nodes", [])
    before = len(nodes)
    graph["nodes"] = [n for n in nodes if n.get("id") not in NOTE_IDS]
    if len(graph["nodes"]) != before:
        changes += 1

    crm = find_node(graph, CRM_TOOL_ID)
    if crm:
        data = crm["data"]
        expected_notes = (
            f"Lead từ chatbot — {{{{#sys.query#}}}} | "
            f"Dịch vụ: {{{{#{LEAD_EXTRACT_ID}.service_interest#}}}} | "
            f"Tên: {{{{#{LEAD_EXTRACT_ID}.customer_name#}}}}"
        )
        params = data.get("tool_parameters") or {}
        notes = params.get("notes_append", {}).get("value", "")
        if notes != expected_notes:
            params["notes_append"] = {"type": "mixed", "value": expected_notes}
            data["tool_parameters"] = params
            changes += 1
        if not data.get("tool_description"):
            data["tool_description"] = (
                "Save or update the Mini CRM lead for the current omnichannel conversation."
            )
            changes += 1
        if not data.get("tool_label"):
            data["tool_label"] = "Save CRM Lead"
            changes += 1
        if data.get("credential_id") is None:
            data.pop("credential_id", None)
            changes += 1

    llm_lead = find_node(graph, LLM_LEAD_ID)
    if llm_lead:
        templates = llm_lead["data"].get("prompt_template") or []
        if templates:
            text = templates[0].get("text") or ""
            if "{#178300003001" in text and "{{#178300003001" not in text:
                templates[0]["text"] = text.replace("{#", "{{#").replace("#}", "#}}")
                llm_lead["data"]["prompt_template"] = templates
                changes += 1

    return changes


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT graph FROM workflows WHERE id = %s", (DRAFT_ID,))
            row = cur.fetchone()
            if not row:
                raise SystemExit("draft not found")
            graph = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            graph = copy.deepcopy(graph)
            changes = fix_graph(graph)
            cur.execute(
                """
                UPDATE workflows
                SET graph = %s::json, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (json.dumps(graph, ensure_ascii=False), DRAFT_ID),
            )
        conn.commit()
        published = publish_draft(conn, APP_ID)
        conn.commit()
        print(f"OK changes={changes} nodes={len(graph['nodes'])} published={published}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
