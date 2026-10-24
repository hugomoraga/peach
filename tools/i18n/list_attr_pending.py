#!/usr/bin/env python3
"""Traduce el texto de los atributos HTML dentro de plantillas.

Casos que el codemod no cubre:

    '<button title="永久删除回收站内容">清空回收站</button>'
    'data-initial="无封面"'

El texto va dentro de comillas dobles, así que no es un literal JS ni JSX
entre tags: es un atributo. Se traduce atributo por atributo.

También cubre las frases con interpolación dentro de JSX:

    >已经导入了 {n} 份浏览器历史。<
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
ROOT = Path("frontend/src")

# Atributos HTML cuyo valor es texto visible para el usuario.
ATTR = re.compile(r'(title|alt|aria-label|placeholder|data-initial|data-placeholder)="([^"]*)"')

# Texto entre tags, partido por interpolaciones.
JSX = re.compile(r">([^<>]+)<")
SEG = re.compile(r"(\{[^{}]*\})")

CODE_MARKERS = re.compile(
    r"=>|&&|\|\||\bfunction\b|\bconst\b|\breturn\b|\bimport\b|"
    r"[A-Za-z_$][\w$]*\s*\([^)]*\)\s*[;{]|"
    r"[<>]=|===|!==|\.\w+\s*\("
)


def attr_segments(text: str) -> list[str]:
    """Trocea el valor de un atributo en texto y expresiones."""
    return SEG.split(text)


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
            value = m.group(2)
            if not CJK.search(value) or value in known:
                continue
            for seg in attr_segments(value):
                seg = seg.strip()
                if CJK.search(seg) and seg not in known:
                    hits.setdefault("ATTR " + seg, rel)
        for m in JSX.finditer(text):
            body = m.group(1)
            if not CJK.search(body):
                continue
            if CODE_MARKERS.search(body) or "/*" in body or "*/" in body:
                continue
            for seg in SEG.split(body):
                seg = seg.strip()
                if CJK.search(seg) and seg not in known:
                    hits.setdefault("JSX " + seg, rel)

    print(f"{len(hits)} tramos pendientes")
    for k, v in sorted(hits.items()):
        print(f"{v}\t{k!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
