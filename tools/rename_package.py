#!/usr/bin/env python3
"""Renombra el paquete Python `peach` a `videodrome`.

El nombre del paquete es técnico, no la marca: `import peach` no aparece en
la interfaz. Renombrarlo deja el código del fork con su propio nombre.

Cuidado con lo que NO se toca: `peach-data`, `videodrome-app`, `peach-sync` y
`peach-worktrees` son rutas de datos y de trabajo, no nombres de módulo. La
sustitución sólo actúa delante de una palabra que_precede_a_una_frase.

Uso:
    tools/i18n/../rename_package.py --dry-run
    tools/i18n/../rename_package.py --apply
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "peach"
NEW = "videodrome"

#: Palabras que sobreviven al renombrado. Son rutas de datos (`peach-data`),
#: nombres de la clase CSS (`peach-react`), el repositorio de upstream y la
#: web de la marca. Cada una se reconoce por el texto que la sigue.
KEEP_AFTER = (
    "-data", "-app", "-sync", "-worktrees", "-react", "-video", "-mitao",
    ".video", "_mitao", ".react", "s", "es",
)
#: Palabras que la anteceden y no se renombran: el repositorio de upstream,
#: el prefijo inverso del bundle y el nombre de la marca.
KEEP_BEFORE = ("longmeidao.peach", "peach-mitao/peach", "hugomoraga/peach",
                "peach-mitao/", "hugomoraga/", "peach-mitao")
#: El repositorio del fork: el de upstream no se renombra, el nuestro sí.
FORK_REPO = "hugomoraga/peach"
#: El repositorio de upstream se queda como está, con su nombre y el suyo.
UPSTREAM_REPO = "peach-mitao/peach"

#: `peach` como módulo, comando o parte de un identificador.
MODULE = re.compile(r"(?<![\w.-])peach\b")
#: El paquete dentro de una ruta: `src/peach/api.py`.
PATH = re.compile(r"(?<=/)peach(?=/)")


def rename_text(text: str) -> tuple[str, int]:
    """Sustituye el nombre de módulo, dejando intactas las rutas de datos."""
    count = 0

    # El repositorio de upstream se aparta antes de nada: su nombre entero no
    # se toca, ni siquiera la parte que coincide con el nombre del paquete.
    text = text.replace(UPSTREAM_REPO, "\0UPSTREAM\0")
    # El del fork pasa a ser el nuestro.
    text, fork_count = re.subn(r"hugomoraga/peach\b", FORK_REPO, text)
    count += fork_count

    def keep_it(start: int, end: int) -> bool:
        """Esta coincidencia forma parte de un nombre que no se renombra."""
        after = text[end:end + 16]
        for suffix in KEEP_AFTER:
            if after.startswith(suffix):
                return True
        before = text[max(0, start - 24):start]
        for prefix in KEEP_BEFORE:
            if before.endswith(prefix):
                return True
        return False

    def replace_module(match: re.Match) -> str:
        nonlocal count
        start, end = match.start(), match.end()
        if keep_it(start, end):
            return match.group(0)
        count += 1
        return NEW

    text, path_count = PATH.subn(NEW, text)
    count += path_count
    text = MODULE.sub(replace_module, text)
    text = text.replace("\0UPSTREAM\0", UPSTREAM_REPO)
    return text, count
#: Ficheros que guardan datos o traducciones, no código: sus textos no se
#: renombran porque hablan del programa como el usuario lo ve.
SKIP = (
    "tools/i18n/glossary.zh-es.json",
    "tools/i18n/coverage-baseline.json",
    "tools/i18n/manual-glossary.json",
    "tools/rename_package.py",
    "web/vendor",
)


def is_skipped(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == skip or rel.startswith(skip) for skip in SKIP)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    targets = [
        path for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and path.suffix in {".py", ".toml", ".spec", ".ps1", ".sh", ".mjs", ".ts", ".tsx", ".js", ".yml", ".yaml"}
        and not any(part in {".git", "node_modules", ".venv", "dist", "build", ".i18n", "__pycache__"}
                    for part in path.relative_to(ROOT).parts)
        and not is_skipped(path)
    ]
    changed: list[tuple[Path, int]] = []
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new, count = rename_text(text)
        if count and new != text:
            changed.append((path, count))
            if args.apply:
                path.write_text(new, encoding="utf-8")
    for path, count in changed:
        print(f"{count:5d}  {path.relative_to(ROOT)}")
    print(f"\n{len(changed)} ficheros, {sum(c for _, c in changed)} sustituciones")
    if not args.apply:
        print("(--dry-run: no se escribió nada)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
