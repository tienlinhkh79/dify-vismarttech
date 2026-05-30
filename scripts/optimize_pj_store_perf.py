"""Performance optimizations for PJ Store workflow (reduce freeze/slow load)."""

from __future__ import annotations

import json
from typing import Any

import psycopg2

WORKFLOW_IDS = (
    "e46ef02f-e392-4e41-870c-040add152a1f",
    "7f65b7b8-52af-445c-a057-d82acaf8f847",
)
QC_NODE = "1711528709608"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}


def optimize_graph(graph: dict[str, Any]) -> int:
    changes = 0
    for node in graph.get("nodes", []):
        data = node.get("data", {})
        nid = node["id"]

        if nid == QC_NODE and data.get("type") == "question-classifier":
            if data.get("vision", {}).get("enabled"):
                data["vision"] = {"enabled": False}
                changes += 1
            model = data.setdefault("model", {})
            if model.get("name") != "gpt-4.1-mini":
                model["name"] = "gpt-4.1-mini"
                changes += 1
            cp = model.setdefault("completion_params", {})
            if cp.get("max_tokens", 512) > 256:
                cp["max_tokens"] = 256
                changes += 1
            if cp.get("temperature", 0.7) > 0.3:
                cp["temperature"] = 0.3
                changes += 1
            mem = data.get("memory") or {}
            win = mem.get("window") or {}
            if win.get("size", 10) > 6:
                mem["window"] = {"enabled": True, "size": 6}
                data["memory"] = mem
                changes += 1

        if data.get("type") == "llm":
            mem = data.get("memory") or {}
            win = mem.get("window") or {}
            if win.get("enabled") and win.get("size", 10) > 6:
                mem["window"] = {"enabled": True, "size": 6}
                data["memory"] = mem
                changes += 1

        if data.get("type") == "parameter-extractor":
            mem = data.get("memory") or {}
            win = mem.get("window") or {}
            if win.get("enabled") and win.get("size", 10) > 4:
                mem["window"] = {"enabled": True, "size": 4}
                data["memory"] = mem
                changes += 1

        # Shrink editor payload: tool nodes store huge paramSchemas copies
        if data.get("type") == "tool" and data.get("paramSchemas"):
            if len(json.dumps(data["paramSchemas"])) > 5000:
                data["paramSchemas"] = []
                changes += 1

    return changes


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        for wf_id in WORKFLOW_IDS:
            with conn.cursor() as cur:
                cur.execute("SELECT graph FROM workflows WHERE id = %s", (wf_id,))
                graph = cur.fetchone()[0]
                if isinstance(graph, str):
                    graph = json.loads(graph)
                n = optimize_graph(graph)
                cur.execute(
                    "UPDATE workflows SET graph = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (json.dumps(graph, ensure_ascii=False), wf_id),
                )
            conn.commit()
            print(f"OK {wf_id}: {n} optimizations")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
