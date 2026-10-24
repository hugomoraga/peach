#!/usr/bin/env python3
"""Diagnóstico: qué formas exactas tienen los literales/JSX sin traducir."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402

CJK = re.compile(r"[一-鿿]")
ROOT = Path("frontend/src")

# Texto JSX entre tags: permite {} (interpolaciones) pero no < ni >.
JSX = re.compile(r">([^<>]+)<")


def main() -> int:
    glossary = json.loads(Path("tools/i18n/glossary.zh-es.json").read_text(encoding="utf-8"))
    known = set(glossary)
    hits: dict[str, str] = {}

    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lit in scan_js(text):
            body = lit.body
            if not CJK.search(body) or body in known:
                continue
            hits.setdefault("LIT " + body, str(path.relative_to(ROOT)))
        for m in JSX.finditer(text):
            body = m.group(1)
            if not CJK.search(body) or body in known:
                continue
            hits.setdefault("JSX " + body, str(path.relative_to(ROOT)))

    print(f"{len(hits)} formas pendientes")
    for k, v in sorted(hits.items()):
        print(f"{v}\t{k!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
