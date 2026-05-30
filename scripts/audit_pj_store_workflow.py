"""Audit PJ Store workflow for broken variable references."""

from __future__ import annotations

import json
from collections import defaultdict

import psycopg2

DRAFT_ID = "e46ef02f-e392-4e41-870c-040add152a1f"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}


def ancestors(node_id: str, in_edges: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        for parent in in_edges.get(current, []):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def main() -> None:
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT graph, conversation_variables FROM workflows WHERE id = %s", (DRAFT_ID,))
    graph_raw, conv_vars_raw = cur.fetchone()
    graph = graph_raw if isinstance(graph_raw, dict) else json.loads(graph_raw)
    conv_vars = conv_vars_raw if isinstance(conv_vars_raw, dict) else json.loads(conv_vars_raw or "{}")

    nodes = {n["id"]: n for n in graph["nodes"]}
    in_e: dict[str, list[str]] = defaultdict(list)
    out_e: dict[str, list[str]] = defaultdict(list)
    for edge in graph["edges"]:
        in_e[edge["target"]].append(edge["source"])
        out_e[edge["source"]].append(edge["target"])

    issues: list[str] = []

    print("=== CONVERSATION VARIABLES ===")
    print(json.dumps(list(conv_vars.keys()), ensure_ascii=False))

    print("\n=== ASSIGNER NODES ===")
    for node in graph["nodes"]:
        if node["data"].get("type") != "assigner":
            continue
        nid = node["id"]
        title = node["data"]["title"]
        anc = ancestors(nid, in_e)
        print(f"\n{title} ({nid})")
        print(f"  direct parents: {[nodes[p]['data']['title'] for p in in_e.get(nid, [])]}")
        for item in node["data"].get("items", []):
            value = item.get("value", [])
            if not isinstance(value, list) or len(value) < 2:
                issues.append(f"{title}: invalid value {value}")
                continue
            src_id, var_name = value[0], value[1]
            src_title = nodes.get(src_id, {}).get("data", {}).get("title", "MISSING")
            ok = src_id in anc
            flag = "OK" if ok else "BROKEN"
            print(f"  [{flag}] {item['variable_selector']} <- {src_title}/{var_name}")
            if not ok:
                issues.append(f"{title}: {var_name} from {src_title} not in same branch")

    print("\n=== IF-ELSE CONDITIONS ===")
    for node in graph["nodes"]:
        if node["data"].get("type") != "if-else":
            continue
        nid = node["id"]
        title = node["data"]["title"]
        anc = ancestors(nid, in_e)
        for case in node["data"].get("cases", []):
            for cond in case.get("conditions", []):
                sel = cond.get("variable_selector", [])
                if len(sel) < 2:
                    continue
                if sel[0] == "conversation":
                    var = sel[1]
                    if var not in conv_vars:
                        issues.append(f"{title}: unknown conversation var {var}")
                        print(f"  [BROKEN] {title}: conversation.{var} not defined")
                    else:
                        print(f"  [OK] {title}: conversation.{var}")
                else:
                    src_id = sel[0]
                    src_title = nodes.get(src_id, {}).get("data", {}).get("title", "MISSING")
                    ok = src_id in anc
                    flag = "OK" if ok else "BROKEN"
                    print(f"  [{flag}] {title}: {src_title}/{sel[1]}")
                    if not ok:
                        issues.append(f"{title}: {sel[1]} from {src_title} not in same branch")

    print("\n=== TEMPLATE NODES ===")
    for node in graph["nodes"]:
        if node["data"].get("type") != "template-transform":
            continue
        nid = node["id"]
        title = node["data"]["title"]
        anc = ancestors(nid, in_e)
        print(f"\n{title}: template={node['data'].get('template', '')[:80]}")
        for var in node["data"].get("variables", []):
            sel = var.get("value_selector", [])
            src_id = sel[0] if sel else "?"
            src_title = nodes.get(src_id, {}).get("data", {}).get("title", src_id)
            ok = src_id in anc or src_id in ("sys", "conversation")
            flag = "OK" if ok else "BROKEN"
            print(f"  [{flag}] {var['variable']} <- {src_title}")
            if not ok:
                issues.append(f"{title}: {var['variable']} from {src_title} not in same branch")

    print("\n=== CODE NODES ===")
    for node in graph["nodes"]:
        if node["data"].get("type") != "code":
            continue
        nid = node["id"]
        title = node["data"]["title"]
        anc = ancestors(nid, in_e)
        for var in node["data"].get("variables", []):
            sel = var.get("value_selector", [])
            if len(sel) < 2:
                continue
            src_id = sel[0]
            src_title = nodes.get(src_id, {}).get("data", {}).get("title", src_id)
            ok = src_id in anc or src_id == "conversation"
            flag = "OK" if ok else "BROKEN"
            print(f"  [{flag}] {title}: {var['variable']} <- {src_title}/{sel[1]}")
            if not ok:
                issues.append(f"{title}: {var['variable']} from {src_title} not in same branch")

    print("\n=== PE NODES (model check) ===")
    for node in graph["nodes"]:
        if node["data"].get("type") != "parameter-extractor":
            continue
        title = node["data"]["title"]
        model = node["data"].get("model", {})
        params = node["data"].get("parameters", [])
        print(f"  {title}: model={model.get('name')}, params={[p['name'] for p in params]}")

    print(f"\n=== TOTAL ISSUES: {len(issues)} ===")
    for issue in issues:
        print(f"  - {issue}")

    conn.close()


if __name__ == "__main__":
    main()
