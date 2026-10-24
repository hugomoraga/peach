#!/usr/bin/env python3
"""Compila el frontend en español sin tocar la fuente versionada.

El árbol de fuentes sigue en el idioma de `upstream`. Este script:

1. copia el repositorio a `.i18n/es/` (ignorando `.git`, dependencias, cachés y
   artefactos);
2. fija el locale de presentación en `es-ES` (fechas, números, orden, documento
   y reproductor);
3. aplica el glosario, los mapas por archivo y una segunda pasada con el AST
   de TypeScript, que alcanza las plantillas que el escáner no ve;
4. comprueba que la cobertura no ha crecido, que los placeholders siguen
   enteros y que los valores de dato llegan intactos;
5. compila la copia con el build crudo de Vite;
6. publica los cuatro archivos de `web/dist/` en el repositorio.

El único cambio versionado que produce es `web/dist/`. La fuente no se modifica.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import (  # noqa: E402
    excluded,
    longest_first,
    translate_python,
    translate_ts,
)

BUNDLES = ("videodrome-app.js", "videodrome-app.css", "videodrome-pages.js", "videodrome-pages.css")
TEXT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".html", ".css"}


def translate_tree(root: Path, glossary: dict[str, str], report: Path) -> None:
    ordered = longest_first(glossary)
    total = 0
    missing: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if excluded(rel):
            continue
        if path.suffix == ".py":
            count, missed = translate_python(path, glossary, ordered)
        else:
            count, missed = translate_ts(path, glossary, ordered)
        total += count
        for item in missed:
            missing.setdefault(item, []).append(rel)
    report.write_text(json.dumps({
        "replacements": total,
        "untranslated_count": len(missing),
        "untranslated": {key: value[:3] for key, value in sorted(missing.items())},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"traducciones aplicadas: {total}")
    print(f"cadenas sin traducir: {len(missing)} -> {report}")


def normalize_region_paths(built: Path) -> None:
    """Deja `//#region node_modules/...` aunque el build corra desde una copia.

    Vite resuelve el symlink de `node_modules` a su ruta real y escribe
    `../../../../../.../node_modules/...` en el bundle. Esa ruta depende de
    dónde esté la copia, así que el artefacto dejaría de ser reproducible y el
    test de rutas estables fallaría.
    """
    pattern = re.compile(r"(?m)^//#region .*?node_modules/")
    for path in built.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        normalized = pattern.sub("//#region node_modules/", text)
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")


def link_node_modules(repo: Path, copy: Path) -> None:
    modules = copy / "frontend" / "node_modules"
    source = repo / "frontend" / "node_modules"
    if not source.is_dir():
        raise SystemExit(f"faltan dependencias del frontend: {source}")
    if modules.exists() or modules.is_symlink():
        return
    modules.symlink_to(source, target_is_directory=True)


#: Llamadas de formato y orden que fijan el locale chino en el código de upstream.
LOCALE_PATTERNS = (
    (re.compile(r"""(toLocale(?:String|DateString|TimeString))\(\s*(['"])zh-CN\2"""), r"\1(\2es-ES\2"),
    (re.compile(r"""(localeCompare\([^,]+,\s*)(['"])zh-CN\2"""), r"\1\2es-ES\2"),
    (re.compile(r"""(setAttribute\(\s*(['"])lang\2\s*,\s*)(['"])zh-CN\3"""), r"\1\3es-ES\3"),
    (re.compile(r"""(language\s*:\s*)(['"])zh-CN\2"""), r"\1\2es-ES\2"),
    (re.compile(r"""(lang\s*=\s*)(['"])zh-CN\2"""), r"\1\2es-ES\2"),
)


def localize_frontend(repo: Path, out: Path) -> None:
    """Fija el locale español en la copia de compilación.

    La fuente sigue en chino. Aquí solo se cambia la presentación: formato de
    fechas y números, orden alfabético, idioma del documento y del reproductor.
    """
    for path in sorted((out / "frontend" / "src").rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for pattern, replacement in LOCALE_PATTERNS:
            new = pattern.sub(replacement, new)
        if new != text:
            path.write_text(new, encoding="utf-8")

    # Las etiquetas genéricas de las fuentes de medios viven en un JSON que el
    # frontend importa en tiempo de compilación. Las marcas (PikPak, 115…)
    # se quedan como están; solo se traducen las que no son nombre propio.
    labels_path = repo / "tools" / "i18n" / "media-sources.es.json"
    registry_path = out / "resources" / "media-sources.json"
    if labels_path.is_file() and registry_path.is_file():
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for row in registry:
            translated = labels.get(row.get("id"))
            if translated:
                row["name"] = translated
                row["label"] = translated
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")

    # Video.js trae el locale español como módulo de datos con hash. Se genera
    # el envoltorio que lo registra y se cambia el módulo que importa el player.
    vendor = out / "web" / "vendor" / "videojs" / "10.1.0"
    spanish = sorted(vendor.glob("es-*.js")) if vendor.is_dir() else []
    if spanish:
        (vendor / "locales").mkdir(parents=True, exist_ok=True)
        (vendor / "locales" / "es.js").write_text(
            '/*! Video.js | locale español generado en el build */\n'
            f'import{{t as e}}from"../{spanish[0].name}";'
            'import{registerI18n as t}from"../i18n.js";t(`es`,e);\n',
            encoding="utf-8",
        )
        player = out / "frontend" / "src" / "player" / "videojs.ts"
        player.write_text(player.read_text(encoding="utf-8").replace(
            "'locales/zh-CN.js'", "'locales/es.js'"), encoding="utf-8")
        for name in ("detail-player.ts", "preview-player.ts"):
            path = out / "frontend" / "src" / "player" / name
            path.write_text(path.read_text(encoding="utf-8").replace(
                "language: 'es-ES'", "language: 'es'"), encoding="utf-8")


def translate_frontend_ast(repo: Path, out: Path) -> None:
    """Segunda pasada con el parser de TypeScript para los literales que el
    escáner de Python no ve (plantillas con comentarios o llaves anidadas)."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("no se encontró node; instala Node 24+")
    script = repo / "tools" / "i18n" / "translate_frontend.mjs"
    completed = subprocess.run(
        [node, str(script),
         "--root", str(out),
         "--modules", str(out / "frontend" / "node_modules"),
         "--glossary", str(repo / "tools" / "i18n" / "glossary.zh-es.json"),
         "--report", str(out / "frontend-report.json")],
        check=False, text=True, encoding="utf-8", errors="replace",
    )
    if completed.returncode != 0:
        raise SystemExit("falló la pasada AST del frontend")


def translate_units(repo: Path, out: Path) -> None:
    """Traduce las unidades de presentación de unos pocos archivos.

    Palabras como `个` (unidades) o `万` (diez mil) se usan en dos sentidos: como
    sufijo que se ve en pantalla y como valor que se guarda. El glosario global
    no puede decidir, así que estos archivos traen su propio mapa: son la
    lista corta y revisable de lo que sí es texto de interfaz.
    """
    overlay_path = repo / "tools" / "i18n" / "units.es.json"
    if not overlay_path.is_file():
        return
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    for rel, units in overlay.items():
        path = out / rel
        if not path.is_file():
            raise SystemExit(f"faltan las unidades declaradas para {rel}")
        text = path.read_text(encoding="utf-8")
        for zh, es in units.items():
            for quote in ("'", '"'):
                pattern = quote + zh + quote
                if pattern in text:
                    text = text.replace(pattern, quote + es + quote)
        path.write_text(text, encoding="utf-8")


def build_frontend(repo: Path, out: Path, glossary_path: Path) -> None:
    glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
    if out.exists():
        shutil.rmtree(out)
    copy_tracked(repo, out)
    link_node_modules(repo, out)
    localize_frontend(repo, out)
    translate_tree(out, glossary, out / "report.json")
    translate_units(repo, out)
    translate_frontend_ast(repo, out)

    # Los valores de datos no pueden salir traducidos del build.
    integrity = subprocess.run(
        [sys.executable, str(repo / "tools" / "i18n" / "check_data.py"),
         "--source", str(repo), "--build", str(out),
         "--labels", str(repo / "tools" / "i18n" / "media-sources.es.json")],
        check=False, text=True, encoding="utf-8", errors="replace",
    )
    if integrity.returncode != 0:
        raise SystemExit("el build alteró valores de datos")

    # La cobertura se mide sobre la fuente, no sobre la copia: así el informe
    # señala la cadena original que falta y no una traducción a medias.
    coverage = subprocess.run(
        [sys.executable, str(repo / "tools" / "i18n" / "coverage.py"),
         "--repo", str(repo), "--check"],
        check=False, text=True, encoding="utf-8", errors="replace",
    )
    if coverage.returncode != 0:
        raise SystemExit("hay cadenas de interfaz nuevas sin traducción; revisa el informe de cobertura")

    validation = subprocess.run(
        [sys.executable, str(repo / "tools" / "i18n" / "validate.py"),
         "--glossary", str(glossary_path), "--tree", str(out), "--skip-syntax"],
        check=False, text=True, encoding="utf-8", errors="replace",
    )
    if validation.returncode != 0:
        raise SystemExit("el glosario rompe placeholders; revisa tools/i18n/report.json")

    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("no se encontró npm; instala Node 24+")
    frontend = out / "frontend"
    completed = subprocess.run(
        [npm, "run", "build:raw"],
        cwd=frontend,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise SystemExit(f"falló el build del frontend en {frontend}")

    built = out / "web" / "dist"
    for name in BUNDLES:
        if not (built / name).is_file():
            raise SystemExit(f"el build no produjo {built / name}")
    normalize_region_paths(built)
    destination = repo / "web" / "dist"
    destination.mkdir(parents=True, exist_ok=True)
    for name in BUNDLES:
        shutil.copy2(built / name, destination / name)
    print(f"publicado -> {destination}")


def copy_tracked(repo: Path, out: Path) -> None:
    """Copia solo los archivos versionados, sin datos, medios ni artefactos.

    `copytree` copiaba el árbol entero salvo unas carpetas. Un checkout real
    puede tener `peach-data/`, medios o cachés enormes; el build no debe
    leerlos ni duplicarlos. La lista sale de `git ls-files`, así que la copia
    es exactamente lo que hay versionado.
    """
    if out.exists():
        shutil.rmtree(out)
    names = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z"],
        text=True, encoding="utf-8", errors="replace",
    ).split("\0")
    for name in names:
        if not name:
            continue
        source = repo / name
        if not source.is_file():
            continue
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path(".i18n/es"))
    parser.add_argument("--glossary", type=Path,
                        default=Path("tools/i18n/glossary.zh-es.json"))
    args = parser.parse_args()

    repo = args.repo.resolve()
    out = (repo / args.out).resolve() if not args.out.is_absolute() else args.out
    glossary = (repo / args.glossary).resolve()
    build_frontend(repo, out, glossary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
