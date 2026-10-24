#!/usr/bin/env python3
"""Re-marca los lotes ya traducidos contra el glosario final.

El extractor cambió (el escáner de plantillas devuelve literales completos),
así que algunas claves de los lotes anteriores quedaron truncadas o
desactualizadas. Este script:

1. Vuelve a partir del último glosario y de los lotes ya traducidos.
2. Detecta literales sin traducción (nuevos o mal extraídos).
3. Escribe un lote con SOLO esos literales, listo para traducir.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402

CJK = re.compile(r"[一-鿿㐀-䶿]")

DATA_SUFFIXES = (
    "genre_taxonomy.py", "catalog_rules.py", "kanji.py", "studio_sites.py",
    "jav-title.ts", "core/tags.ts",
)
SKIP_PARTS = {"node_modules", ".venv", "build", "vendor", "test", "tests",
              "docs", "dist", ".i18n"}


def is_data(rel: str) -> bool:
    """True si el archivo guarda o compara valores de base de datos.

    Etiquetas de contenido, géneros, kanji y nombres de estudio: son la
    verdad que se compara contra fuentes japonesas. Traducirlos rompería
    el matching, así que no entran ni en el glosario ni en la traducción.
    """
    return any(rel.endswith(s) for s in DATA_SUFFIXES)


def collect(root: Path) -> dict[str, list[str]]:
    """Todos los literales con CJK que están en archivos de interfaz."""
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in {".ts", ".tsx"}:
            if any(p in SKIP_PARTS for p in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if is_data(rel):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lit in scan_js(text):
                body = lit.body
                if CJK.search(body) and len(body) <= 300:
                    line = text.count("\n", 0, lit.start) + 1
                    found.setdefault(body, []).append(f"{rel}:{line}")
        elif path.suffix == ".py":
            if any(p in SKIP_PARTS for p in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if is_data(rel):
                continue
            found.update({})
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--batches", type=Path, default=Path("tools/i18n/out"))
    parser.add_argument("--glossary", type=Path, default=Path("tools/i18n/glossary.zh-es.json"))
    parser.add_argument("--out", type=Path, default=Path("tools/i18n/pending.json"))
    args = parser.parse_args()

    # 1. lo ya traducido
    translated: dict[str, str] = {}
    for path in sorted(args.batches.glob("batch_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in data.get("items", []):
            zh, es = item.get("zh", ""), item.get("es", "")
            if zh and es:
                translated[zh] = es

    # 2. el glosario actual manda sobre lo anterior
    glossary = json.loads(args.glossary.read_text(encoding="utf-8"))
    translated.update(glossary)

    # 3. todo lo que hay en el código
    source = json.loads((args.root / "tools/i18n/glossary_source.json").read_text(encoding="utf-8"))
    pending: dict[str, list[str]] = {}
    for kind in ("frontend", "python"):
        for literal, places in source.get(kind, {}).items():
            if literal in translated or not CJK.search(literal):
                continue
            # Si TODAS sus apariciones están en archivos de datos, no es UI.
            if places and all(is_data(p.split(":")[0]) for p in places):
                continue
            pending.setdefault(literal, [])
            for loc in places:
                if loc not in pending[literal]:
                    pending[literal].append(loc)

    items = [{"zh": lit, "es": ""} for lit in sorted(pending)]
    payload = {
        "items": items,
        "context": {lit: pending[lit][:3] for lit in sorted(pending)},
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"traducidas: {len(translated)}")
    print(f"pendientes: {len(items)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
