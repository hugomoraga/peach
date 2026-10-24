#!/usr/bin/env python3
"""Informa qué cadenas de interfaz no tienen traducción.

La fuente sigue en chino. Este informe es una ratchet: la línea base guarda las
cadenas pendientes que ya existían; una cadena nueva sin traducción hace fallar
la comprobación. Así el trabajo pendiente es visible y no crece por accidente.

Uso:
    tools/i18n/coverage.py --check
    tools/i18n/coverage.py --update-baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_strings import frontend_literals, python_literals  # noqa: E402
from translate import excluded  # noqa: E402


def _visible(locations: list[str]) -> list[str]:
    """Descarta ubicaciones de archivos que no son interfaz (datos, tests, tools)."""
    return [location for location in locations if not excluded(location.split(":", 1)[0])]


def _excluded_values(root: Path) -> set[str]:
    """Valores que son dato y no interfaz: no se traducen y no cuentan.

    Los declara el lote manual que los saca del glosario. Si uno apareciera
    como pendiente, la ratchet lo marcaría como cadena nueva sin traducir
    cuando en realidad es un valor que se guarda.
    """
    path = root / "tools" / "i18n" / "manual-glossary-10.json"
    if not path.is_file():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("exclude", []))


def pending(root: Path, glossary: dict[str, str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    data = _excluded_values(root)
    for group in (frontend_literals(root / "frontend" / "src"),
                  python_literals(root / "src")):
        for text, locations in group.items():
            shown = _visible(locations)
            if not shown or text in glossary or text in data:
                continue
            found[text] = shown
    return dict(sorted(found.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--glossary", type=Path,
                        default=Path("tools/i18n/glossary.zh-es.json"))
    parser.add_argument("--baseline", type=Path,
                        default=Path("tools/i18n/coverage-baseline.json"))
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = args.repo.resolve()
    glossary = json.loads((root / args.glossary).read_text(encoding="utf-8"))
    missing = pending(root, glossary)
    baseline_path = root / args.baseline
    baseline = set()
    if baseline_path.is_file():
        baseline = set(json.loads(baseline_path.read_text(encoding="utf-8")))

    if args.update_baseline:
        baseline_path.write_text(
            json.dumps(sorted(missing), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"línea base actualizada: {len(missing)} cadenas -> {baseline_path}")
        return 0

    new = sorted(set(missing) - baseline)
    recovered = sorted(baseline - set(missing))
    print(f"cadenas de interfaz sin traducir: {len(missing)}")
    print(f"línea base: {len(baseline)}")
    if recovered:
        print(f"resueltas desde la línea base: {len(recovered)} (actualiza la línea base)")
    if new:
        print(f"nuevas sin traducir: {len(new)}")
        for text in new[:40]:
            locations = missing[text][:2]
            print(f"  {text!r}  {', '.join(locations)}")
        if len(new) > 40:
            print(f"  … y {len(new) - 40} más")
    if args.check and new:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
