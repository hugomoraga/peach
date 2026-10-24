#!/usr/bin/env python3
"""Comprueba que el build español no haya traducido valores de datos.

La traducción solo puede tocar texto de interfaz. Este control compara los
archivos que son fuente de verdad (etiquetas, géneros, kanji, estudios,
títulos JAV) y el registro de fuentes de medios: en este último solo pueden
cambiar `name`/`label` de las fuentes declaradas como etiqueta genérica.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

#: Archivos que deben llegar al build byte a byte iguales que en la fuente.
IDENTICAL = (
    "frontend/src/core/tags.ts",
    "frontend/src/core/jav-title.ts",
    "src/videodrome/genre_taxonomy.py",
    "src/videodrome/catalog_rules.py",
    "src/videodrome/kanji.py",
    "src/videodrome/studio_sites.py",
)

#: Constantes que son valores guardados en la base de datos. Traducirlas
#: cambia lo que se escribe y lo que se consulta: el build compara las bandas
#: una a una en vez de comparar el archivo entero, porque el resto del
#: archivo sí lleva texto de interfaz.


def _constants(path: Path) -> dict[str, object]:
    """Valor literal de las constantes de nivel superior de un módulo Python."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            try:
                found[target.id] = ast.literal_eval(node.value)
            except ValueError:
                continue
    return found


def _band_values(path: Path) -> tuple[str, ...]:
    """Los valores de las bandas de duración y calidad, tal cual se guardan."""
    constants = _constants(path)
    values: list[str] = []
    for name in ("LENGTH_BANDS", "QUALITY_BANDS"):
        value = constants.get(name)
        if isinstance(value, (tuple, list)):
            values.extend(str(item) for item in value)
    return tuple(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--build", type=Path, default=Path(".i18n/es"))
    parser.add_argument("--labels", type=Path, default=Path("tools/i18n/media-sources.es.json"))
    args = parser.parse_args()

    problems: list[str] = []

    for rel in IDENTICAL:
        source, build = args.source / rel, args.build / rel
        if not source.is_file():
            problems.append(f"falta en la fuente: {rel}")
            continue
        if not build.is_file():
            problems.append(f"falta en el build: {rel}")
            continue
        if source.read_bytes() != build.read_bytes():
            problems.append(f"valor de dato modificado: {rel}")

    bands_source = args.source / "src/videodrome/web_stats.py"
    bands_build = args.build / "src/videodrome/web_stats.py"
    if bands_source.is_file() and bands_build.is_file():
        before, after = _band_values(bands_source), _band_values(bands_build)
        if before != after:
            problems.append(f"bandas de duración o calidad modificadas: {before} -> {after}")

    registry_source = args.source / "resources" / "media-sources.json"
    registry_build = args.build / "resources" / "media-sources.json"
    labels = json.loads(args.labels.read_text(encoding="utf-8")) if args.labels.is_file() else {}
    if registry_source.is_file() and registry_build.is_file():
        before = json.loads(registry_source.read_text(encoding="utf-8"))
        after = json.loads(registry_build.read_text(encoding="utf-8"))
        if len(before) != len(after):
            problems.append("el registro de fuentes cambió de tamaño")
        by_id = {row.get("id"): row for row in after}
        for row in before:
            other = by_id.get(row.get("id"))
            if other is None:
                problems.append(f"fuente eliminada: {row.get('id')}")
                continue
            allowed = {"name", "label"} if row.get("id") in labels else set()
            for key, value in row.items():
                if key in allowed:
                    continue
                if other.get(key) != value:
                    problems.append(f"campo de dato cambiado en {row.get('id')}.{key}")

    if problems:
        print("datos alterados en el build español:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("integridad de datos: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
