#!/usr/bin/env python3
"""Reescribe un glosario manual usando las cadenas EXACTAS del código fuente.

El problema: el glosario se escribió a ojo, con un nivel de escapado distinto
al del código. En el fuente, el HTML va como `title=\"永久删除…\"` (con
backslash); en el JSON del glosario hay que escribirlo igual, no con `\\\"`.

Este script toma las claves del glosario manual, busca en el código fuente la
cadena real que corresponde (normalizando escapes) y devuelve el JSON con las
claves corregidas.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402


def unescape(text: str) -> str:
    """Convierte la representación JSON de una cadena en su valor real."""
    try:
        return json.loads(f'"{text}"')
    except Exception:
        return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glossary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("frontend/src"))
    args = parser.parse_args()

    data = json.loads(args.glossary.read_text(encoding="utf-8"))
    terms = data.get("terms", {})

    # todas las cadenas literales del código, con su forma exacta
    exact: dict[str, str] = {}
    for path in sorted(args.root.rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lit in scan_js(text):
            exact.setdefault(lit.body, lit.body)

    fixed: dict[str, str] = {}
    missing: list[str] = []
    for key, value in terms.items():
        if key in exact:
            fixed[key] = value
            continue
        # la clave del glosario puede llevar escapes que el código no lleva
        plain = unescape(key)
        if plain in exact:
            fixed[plain] = value
            continue
        # o al revés: el código tiene escapes que el glosario no
        if key.replace('\\"', '"') in exact:
            fixed[key.replace('\\"', '"')] = value
            continue
        missing.append(key)

    args.out.write_text(
        json.dumps({"_nota": data.get("_nota", ""), "terms": fixed},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"corregidas: {len(fixed)} / {len(terms)}")
    if missing:
        print(f"no encontradas en el código: {len(missing)}")
        for m in missing[:10]:
            print(f"   {m!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
