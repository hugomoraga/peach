#!/usr/bin/env python3
"""Lista los tramos de UI que quedan sin traducir, ya con su forma EXACTA.

Reúne lo que el codemod no pudo aplicar:
  - tramos de JSX (texto entre tags, partido por interpolaciones),
  - valores de atributos HTML,
  - y los indica con el prefijo del tipo de coincidencia.

La clave del glosario debe ser el tramo tal cual aparece, con sus espacios.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
ROOT = Path("frontend/src")

ATTR = re.compile(
    r'(title|alt|aria-label|placeholder|data-initial|data-placeholder)="([^"]*)"'
)
JSX = re.compile(r">([^<>]+)<")
SEG = re.compile(r"(\{[^{}]*\})")
CODE_MARKERS = re.compile(
    r"=>|&&|\|\||\bfunction\b|\bconst\b|\breturn\b|\bimport\b|"
    r"[A-Za-z_$][\w$]*\s*\([^)]*\)\s*[;{]|"
    r"[<>]=|===|!==|\.\w+\s*\("
)


def is_code(body: str) -> bool:
    if CODE_MARKERS.search(body):
        return True
    if "/*" in body or "*/" in body:
        return True
    if "{" in body or "}" in body:
        return True
    if "?" in body or ":" in body:
        return True
    if "/>" in body:
        return True
    return False


def main() -> int:
    glossary = json.loads(Path("tools/i18n/glossary.zh-es.json").read_text(encoding="utf-8"))
    known = set(glossary)
    hits: dict[str, str] = {}

    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT))

        for m in ATTR.finditer(text):
            for seg in SEG.split(m.group(2)):
                if CJK.search(seg) and seg.strip() not in known:
                    hits.setdefault(seg, rel)

        for m in JSX.finditer(text):
            body = m.group(1)
            if not CJK.search(body) or is_code(body):
                continue
            for seg in SEG.split(body):
                if CJK.search(seg) and seg.strip() not in known:
                    hits.setdefault(seg, rel)

    print(f"{len(hits)} tramos pendientes")
    for k, v in sorted(hits.items()):
        print(f"{v}\t{k!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
