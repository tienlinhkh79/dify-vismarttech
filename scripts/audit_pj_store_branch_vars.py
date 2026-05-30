"""Simulate Dify checklist variable validation for PJ Store workflow."""

from __future__ import annotations

import json
import re
from collections import defaultdict

import psycopg2

DRAFT_ID = "e46ef02f-e392-4e41-870c-040add152a1f"
SPECIAL = {"sys", "env", "conversation", "rag"}
VAR_PATTERN = re.compile(r"\{\{#([^.#]+)\.([^#]+)#\}\}")

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}


def ancestors(node_id: str, in_e: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        for parent in in_e.get(current, []):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def pe_outputs(data: dict) -> list[str]:
    return [p["name"] for p in data.get("parameters", [])]


def node_outputs(node: dict) -> list[str]:
    data = node["data"]
    t = data.get("type")
    if t == "parameter-extractor":
        return pe_outputs(data) + ["__is_success", "__reason", "__usage"]
    if t == "tool":
        return ["text", "files", "json"]
    if t == "code":
        return list((data.get("outputs") or {}).keys())
    if t == "template-transform":
        return ["output"]
    if t == "llm":
        return ["text", "reasoning_content", "usage"]
    if t == "if-else":
        return ["result", "selected_case_id"]
    if t == "assigner":
        return []
    if t == "question-classifier":
        return ["class_name", "class_id", "usage"]
    if t == "answer":
        return ["answer", "files"]
    return []


def extract_used_vars(node: dict) -> list[list[str]]:
    data = node["data"]
    t = data.get("type")
    used: list[list[str]] = []

    def add(sel: list[str] | None) -> None:
        if sel and len(sel) >= 2:
            used.append(sel)

    if t == "assigner":
        for item in data.get("items", []):
            add(item.get("variable_selector"))
            val = item.get("value")
            if isinstance(val, list) and len(val) >= 2:
                add(val)
    elif t == "if-else":
        for case in data.get("cases", []):
            for cond in case.get("conditions", []):
                add(cond.get("variable_selector"))
    elif t == "code":
        for var in data.get("variables", []):
            add(var.get("value_selector"))
    elif t == "template-transform":
        for var in data.get("variables", []):
            add(var.get("value_selector"))
    elif t == "tool":
        for param in (data.get("tool_parameters") or {}).values():
            val = param.get("value")
            if isinstance(val, str):
                for m in VAR_PATTERN.finditer(val):
                    used.append([m.group(1), m.group(2)])
    elif t == "llm":
        for pt in data.get("prompt_template", []):
            text = pt.get("text", "")
            for m in VAR_PATTERN.finditer(text):
                used.append([m.group(1), m.group(2)])
    elif t == "answer":
        text = data.get("answer", "")
        for m in VAR_PATTERN.finditer(text):
            used.append([m.group(1), m.group(2)])
    return used


def main() -> None:
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT graph FROM workflows WHERE id = %s", (DRAFT_ID,))
    graph = cur.fetchone()[0]
    if isinstance(graph, str):
        graph = json.loads(graph)

    nodes = {n["id"]: n for n in graph["nodes"]}
    in_e: dict[str, list[str]] = defaultdict(list)
    for e in graph["edges"]:
        in_e[e["target"]].append(e["source"])

    issues: list[str] = []
    for node in graph["nodes"]:
        nid = node["id"]
        title = node["data"]["title"]
        anc = ancestors(nid, in_e)
        out_map = {src: node_outputs(nodes[src]) for src in anc if src in nodes}
        for sel in extract_used_vars(node):
            if sel[0] in SPECIAL:
                continue
            src_id = sel[0]
            var_name = sel[1]
            if src_id not in anc:
                issues.append(f"{title} ({nid}): {var_name} from {nodes.get(src_id, {}).get('data', {}).get('title', src_id)} NOT in branch")
            elif var_name not in out_map.get(src_id, []):
                issues.append(f"{title} ({nid}): {var_name} missing on {nodes.get(src_id, {}).get('data', {}).get('title', src_id)}")

    print(f"Issues: {len(issues)}")
    for i in issues:
        print(" -", i)
    conn.close()


if __name__ == "__main__":
    main()
