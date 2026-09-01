#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    failures = []
    resolved = 0
    for source in ROOT.rglob("*.md"):
        if ".git" in source.parts:
            continue
        for raw in LINK.findall(source.read_text()):
            target = raw.strip().split(" ", 1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_text = unquote(target.split("#", 1)[0])
            target_path = (source.parent / path_text).resolve()
            if ROOT not in target_path.parents and target_path != ROOT:
                failures.append(f"{source.relative_to(ROOT)}: path leaves repository: {target}")
            elif not target_path.exists():
                failures.append(f"{source.relative_to(ROOT)}: missing {target}")
            else:
                resolved += 1
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Resolved {resolved} local Markdown links and assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
