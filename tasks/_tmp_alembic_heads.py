import re
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
revs: dict[str, str] = {}
downs: set[str] = set()
for p in root.glob("*.py"):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"skip {p.name}: {exc}")
        continue
    m = re.search(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", t, re.M)
    if not m:
        continue
    rev = m.group(1)
    revs[rev] = p.name
    dm = re.search(r"^down_revision\s*[:=]\s*(.+)$", t, re.M)
    if not dm:
        continue
    down = dm.group(1).strip()
    if down == "None":
        continue
    downs.update(re.findall(r"['\"]([^'\"]+)['\"]", down))

heads = sorted(set(revs) - downs)
print(f"HEADS ({len(heads)}):")
for h in heads:
    print(f"{h} -> {revs[h]}")
