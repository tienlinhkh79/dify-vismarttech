import re
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
by_rev: dict[str, list[str] | None] = {}
for p in root.glob("*.py"):
    if p.is_dir():
        print(f"DIR(!): {p.name}")
        continue
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"skip {p.name}: {exc}")
        continue
    m = re.search(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", t, re.M)
    if not m:
        continue
    dm = re.search(r"^down_revision\s*[:=]\s*(.+)$", t, re.M)
    down: list[str] | None = None
    if dm:
        raw = dm.group(1).strip()
        if raw != "None":
            ids = re.findall(r"['\"]([^'\"]+)['\"]", raw)
            down = ids
    by_rev[m.group(1)] = down


def ancestors(rev: str, seen: set[str] | None = None) -> set[str]:
    seen = seen or set()
    if rev in seen or rev not in by_rev:
        return seen
    seen.add(rev)
    d = by_rev[rev]
    if not d:
        return seen
    for x in d:
        ancestors(x, seen)
    return seen


anc = ancestors("d9e8f7a6b5c4")
print("a4f2 in d9e8 ancestors?", "a4f2d8c9b731" in anc)
print("k7 in d9e8 ancestors?", "k7l8m9n0o1p2" in anc)
print("j6 in d9e8 ancestors?", "j6k7l8m9n0o1" in anc)
print("path length", len(anc))
