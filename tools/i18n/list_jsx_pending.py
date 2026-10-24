#!/usr/bin/env python3
"""Lista los tramos de texto JSX pendientes de traducir.

El codemod traduce cada tramo de texto entre `>`/`<` por separado, así que
las claves del glosario son los tramos exactos, no el JSX completo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
ROOT = Path("frontend/src")
JSX = re.compile(r">([^<>]+)<")
SEG = re.compile(r"(\{[^{}]*\})")
CODE_MARKERS = re.compile(
    r"=>|&&|\|\||\bfunction\b|\bconst\b|\breturn\b|\bimport\b|"
    r"[A-Za-z_$][\w$]*\s*\([^)]*\)\s*[;{]|"
    r"[<>]=|===|!==|\.\w+\s*\("
)


def main() -> int:
    glossary = json.loads(Path("tools/i18n/glossary.zh-es.json").read_text(encoding="utf-8"))
    known = set(glossary)
    hits: dict[str, str] = {}

    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in JSX.finditer(text):
            body = m.group(1)
            if not CJK.search(body):
                continue
            if CODE_MARKERS.search(body) or "/*" in body or "*/" in body:
                continue
            for seg in SEG.split(body):
                seg = seg.strip()
                if not CJK.search(seg) or seg in known:
                    continue
                hits.setdefault(seg, str(path.relative_to(ROOT)))

    print(f"{len(hits)} tramos pendientes")
    Path("tools/i18n/pending-ui.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for k, v in sorted(hits.items()):
        print(f"{v}\t{k!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
