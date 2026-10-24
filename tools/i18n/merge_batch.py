#!/usr/bin/env python3
"""Integra un lote traducido por OpenCode en el glosario.

El traductor devuelve un JSON con la misma forma que el lote de entrada:
cada item lleva su clave original en `zh` y la traducción en `es`. Los items
sin traducción (los que no son texto de interfaz) llegan con `es` vacío y se
descartan: se quedan en chino a propósito.

Uso: tools/i18n/merge_batch.py <lote_entrada.json> <salida_traducida.json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CJK = re.compile(r"[一-鿿㐀-䶿]")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])

    items = json.loads(src.read_text(encoding="utf-8"))
    # La salida del traductor puede venir envuelta en texto o con ```json.
    raw = out.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lstrip().startswith("json"):
            raw = raw.lstrip()[4:]
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        print("no se encuentra el array JSON en la salida")
        return 1
    translated = json.loads(raw[start : end + 1])

    terms: dict[str, str] = {}
    skipped = 0
    for item in translated:
        zh = item.get("zh", "")
        es = item.get("es", "")
        if not zh or not es:
            skipped += 1
            continue
        # Sólo entra texto de interfaz: si la traducción trae chino, no se
        # ha traducido y se descarta.
        if CJK.search(es):
            skipped += 1
            continue
        terms[zh] = es

    print(f"traducidos: {len(terms)}   descartados: {skipped}")
    print(f"entradas del lote: {len(items)}")

    # Se escribe como glosario manual, que tiene prioridad sobre los lotes
    # automáticos en build_glossary.py.
    if len(sys.argv) > 3:
        target = Path(sys.argv[3])
        target.write_text(
            json.dumps(
                {
                    "_nota": "Lote traducido: los textos que sólo aparecen en los tests.",
                    "terms": dict(sorted(terms.items())),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"escrito {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
