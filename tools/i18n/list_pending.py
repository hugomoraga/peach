#!/usr/bin/env python3
"""Saca los literales exactos del código que el codemod no traduce.

Criterio: un literal pendiente es aquel que contiene chino, no está en el
glosario, y su texto NO se puede componer con sustituciones parciales. Son
los casos donde el codemod haría una traducción fragmentada o donde el texto
vive en un nodo JSX con interpolaciones.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402

CJK = re.compile(r"[一-鿿]")
ROOT = Path("frontend/src")


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
            if not CJK.search(body) or len(body) > 800 or body in known:
                continue
            if "\n" in body.strip():
                continue
            hits.setdefault(body, str(path.relative_to(ROOT)))

    out = Path("tools/i18n/pending-ui.json")
    out.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(hits)} literales pendientes -> {out}")
    for i, (k, v) in enumerate(hits.items()):
        print(f"{i}\t{v}\t{k!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
