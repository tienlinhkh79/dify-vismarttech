import json

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

vieclam = load(r"c:\chatbot\dify\scripts\tmp_vieclam_graph.json")
pj = load(r"c:\chatbot\dify\scripts\tmp_pj_graph.json")

for label, graph, assign_id in [
    ("vieclam", vieclam, "178100004001"),
    ("pj", pj, "177999010004"),
]:
    node = next(n for n in graph["nodes"] if n["id"] == assign_id)
    print(f"\n=== {label} assigner {assign_id} ===")
    print(json.dumps(node["data"], indent=2, ensure_ascii=False)[:2000])

conv = load(r"c:\chatbot\dify\scripts\tmp_vieclam_conv.json")
print("\n=== vieclam conv vars keys ===")
print(list(conv.keys()))
