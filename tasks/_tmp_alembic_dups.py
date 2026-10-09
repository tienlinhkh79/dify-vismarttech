import collections
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "migrations/versions")
by_rev: dict[str, list[str]] = collections.defaultdict(list)
downs: set[str] = set()
for p in sorted(root.glob("*.py")):
    if p.is_dir():
        print("DIR", p.name)
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", t, re.M)
    if not m:
        continue
    rev = m.group(1)
    by_rev[rev].append(p.name)
    dm = re.search(r"^down_revision\s*[:=]\s*(.+)$", t, re.M)
    if dm:
        raw = dm.group(1).strip()
        if raw != "None":
            downs.update(re.findall(r"['\"]([^'\"]+)['\"]", raw))

dups = {k: v for k, v in by_rev.items() if len(v) > 1}
print(f"DUPS ({len(dups)}):")
for k, v in sorted(dups.items()):
    print(f"  {k} -> {v}")
heads = sorted(set(by_rev) - downs)
print(f"HEADS ({len(heads)}):")
for h in heads:
    print(f"  {h} -> {by_rev[h]}")
print("children of f4e8c9a0b1d2:")
for rev, files in by_rev.items():
    for name in files:
        t = (root / name).read_text(encoding="utf-8", errors="ignore")
        if re.search(r"down_revision.*f4e8c9a0b1d2", t):
            print(f"  {rev} -> {name}")
