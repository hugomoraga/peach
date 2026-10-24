#!/usr/bin/env python3
"""Prepara lotes de traducción con contexto para Claude Code.

Cada lote es un JSON con:
  - "items": [{"zh": ..., "es": ...}]  (es vacío = pendiente)
  - "context": {"<zh>": ["archivo.ts:12", ...]}

El contexto importa: la misma palabra china significa cosas distintas según
dónde aparece. Sin él, «关注» puede terminar siendo «preocupación» en vez de
«seguir».
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CJK = re.compile(r"[一-鿿㐀-䶿]")

# Archivos cuyo chino es DATO (base de datos), no interfaz.
# Se comparan por sufijo: las rutas reales son relativas a src/ o frontend/src/.
DATA_FILES = (
    "genre_taxonomy.py",
    "catalog_rules.py",
    "kanji.py",
    "studio_sites.py",
    "jav-title.ts",
    "core/tags.ts",
)

# Patrones que delatan valores de datos dentro de otros archivos.
DATA_ONLY = re.compile(
    r"^[一-鿿]{1,6}$"          # 2-6 CJK, típico de tag/genio/alias
    r"|^[A-Z]{2,5}\d{2,4}$"    # COD-123
    r"|^https?://"
    r"|^[a-z_]+$"
)


def load_source(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_data_file(rel: str) -> bool:
    """True si el archivo guarda o compara valores, no si muestra interfaz."""
    return any(rel.endswith(suffix) for suffix in DATA_FILES)


def build_items(source: dict) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Devuelve (contexto, categoria) donde categoria ∈ {frontend, python}."""
    context: dict[str, list[str]] = {}
    category: dict[str, str] = {}
    for kind in ("frontend", "python"):
        for literal, places in source.get(kind, {}).items():
            if not CJK.search(literal):
                continue
            locs = places
            rel = locs[0].split(":")[0]
            if is_data_file(rel):
                continue
            context.setdefault(literal, [])
            for loc in locs:
                if loc not in context[literal]:
                    context[literal].append(loc)
            category.setdefault(literal, kind)
    return context, category


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("tools/i18n/glossary_source.json"))
    parser.add_argument("--out", type=Path, default=Path("tools/i18n/batches"))
    parser.add_argument("--size", type=int, default=120)
    args = parser.parse_args()

    source = load_source(args.source)
    context, category = build_items(source)

    literals = sorted(context, key=lambda s: (category[s], len(s), s))
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("batch_*.json"):
        old.unlink()

    total = len(literals)
    batches = []
    for start in range(0, total, args.size):
        chunk = literals[start : start + args.size]
        payload = {
            "items": [{"zh": lit, "es": ""} for lit in chunk],
            "context": {lit: context[lit][:3] for lit in chunk},
        }
        path = args.out / f"batch_{start // args.size:03d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        batches.append(path)

    print(f"literales: {total}")
    print(f"lotes: {len(batches)} (tamaño {args.size})")
    for path in batches[:5]:
        print(f"  {path.name}: {len(json.loads(path.read_text())['items'])} items")
    if len(batches) > 5:
        print(f"  ... y {len(batches) - 5} más")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
