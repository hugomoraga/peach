#!/usr/bin/env python3
"""Valida el glosario y el árbol traducido.

Tres comprobaciones:

1. Placeholders: un placeholder como ${n} o {count} debe sobrevivir intacto.
   Los placeholders que contienen texto chino (${x ? '甲' : '乙'}) sí cambian
   por dentro: lo que importa es que la ESTRUCTURA siga siendo válida.

2. Código generado: el árbol traducido debe seguir siendo JavaScript/TypeScript
   o Python válido. Un error de sintaxis rompe la app entera.

3. Chino residual: cadenas con CJK que quedaron sin traducir en archivos de
   interfaz. Se listan para revisión manual.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

CJK = re.compile(r"[一-鿿㐀-䶿]")

# Placeholders "de estructura": los que el runtime sustituye.
# Se emparejan por llaves balanceadas: `${a.b(c)}` es UN placeholder, y su
# interior puede contener texto chino que sí se traduce.
STRUCTURAL = re.compile(r"%\(\w+\)[sd]|%(?:\d+\$)?[sd]")


def structural_placeholders(text: str) -> list[str]:
    """Placeholders de estructura, con las llaves balanceadas.

    `${a ? '甲' : '乙'}` cuenta como un placeholder: lo que se traduce es su
    interior, no la estructura.
    """
    found: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "$" and i + 1 < n and text[i + 1] == "{":
            depth = 0
            j = i + 1
            while j < n:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n:
                found.append(text[i : j + 1])
                i = j + 1
                continue
            i += 1
            continue
        if text[i] == "{":
            # `{name}` o `{0}`: identificador simple, sin CJK dentro
            m = re.match(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}|\{\d+\}", text[i:])
            if m:
                found.append(m.group(0))
                i += len(m.group(0))
                continue
        i += 1
    found.extend(STRUCTURAL.findall(text))
    return sorted(found)


def check_placeholders(glossary: dict[str, str]) -> list[dict]:
    """Placeholders cuya ESTRUCTURA cambió.

    Un placeholder es `${expresión}`. Al traducir, su interior puede cambiar
    (por ejemplo `${x ? '甲' : '乙'}` → `${x ? 'A' : 'B'}`): eso es correcto.
    Lo que rompería la app es que la estructura cambie: que aparezca o
    desaparezca un `${`, o que el nivel de llaves se desbalance.

    Por eso se comparan las "estructuras": la secuencia de caracteres
    delimitadores, con el interior reducido a un marcador.
    """
    broken = []
    for zh, es in glossary.items():
        a = structural_shape(zh)
        b = structural_shape(es)
        # Una clave truncada en el glosario no es un error de traducción:
        # es un artefacto de una extracción anterior.
        if any("${UNTERMINADO" in item for item in a):
            continue
        # El orden de los placeholders puede cambiar: en español el orden
        # natural es distinto ("${a} de ${b}" → "${b} de ${a}"). Lo que no
        # puede cambiar es el conjunto.
        if sorted(a) != sorted(b):
            broken.append({"zh": zh, "es": es, "expected": sorted(a), "got": sorted(b)})
    return broken


def structural_shape(text: str) -> list[str]:
    """Estructura de los placeholders: '${', '}', '{', '}' y los identificadores.

    Los identificadores de las expresiones (x, count, asset.id) se conservan;
    los textos traducibles dentro de comillas se reducen a ''.
    """
    shape: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "$" and i + 1 < n and text[i + 1] == "{":
            depth = 0
            j = i + 1
            inner = []
            while j < n:
                ch = text[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:
                shape.append("${UNTERMINADO")
                break
            inner = text[i + 2 : j]
            shape.append("${" + shape_of_expression(inner) + "}")
            i = j + 1
            continue
        if text[i] == "{":
            m = re.match(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}|\{\d+\}", text[i:])
            if m:
                shape.append(m.group(0))
                i += len(m.group(0))
                continue
        i += 1
    shape.extend(sorted(STRUCTURAL.findall(text)))
    return shape


def shape_of_expression(expr: str) -> str:
    """Reduce una expresión de interpolación a su estructura.

    Los textos entre comillas se vacían (son traducibles); el resto
    (identificadores, operadores, llaves) se conserva.
    """
    out = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch in "\"'`":
            j = expr.find(ch, i + 1)
            if j < 0:
                out.append(ch)
                break
            out.append("''")
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def check_syntax(root: Path) -> list[str]:
    """Comprueba que el JS/TS y el Python del árbol traducido siguen compilando."""
    errors: list[str] = []

    # Python: compilar cada archivo
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".venv", "build", "node_modules")):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python {rel}:{exc.lineno} {exc.msg}")

    # TypeScript/JS: usar el compilador del frontend si está disponible
    ts_files = [
        p for p in sorted(root.rglob("*.ts"))
        if "node_modules" not in p.parts and ".venv" not in p.parts
    ] + [
        p for p in sorted(root.rglob("*.tsx"))
        if "node_modules" not in p.parts and ".venv" not in p.parts
    ]
    if ts_files:
        tsc = root / "frontend" / "node_modules" / ".bin" / "tsc"
        if tsc.exists():
            proc = subprocess.run(
                [str(tsc), "--noEmit", "--jsx", "react-jsx", "--target", "es2022",
                 "--module", "esnext", "--moduleResolution", "bundler",
                 "--skipLibCheck", "--allowJs", "--noResolve",
                 *[str(p) for p in ts_files]],
                capture_output=True, text=True, cwd=root,
            )
            if proc.returncode != 0:
                lines = [l for l in proc.stdout.split("\n") if "error TS" in l]
                errors.extend(lines[:40])
                if len(lines) > 40:
                    errors.append(f"... y {len(lines) - 40} errores más")
    return errors


def residual_cjk(root: Path, excluded: tuple[str, ...]) -> dict[str, int]:
    """Cadenas con CJK que quedaron en el árbol, por archivo.

    Respeta las mismas exclusiones que `translate.py`: sólo interesan los
    archivos que son interfaz de verdad.
    """
    from fnmatch import fnmatch

    exclude_globs = (
        "web/vendor/*", "web/dist/*", "frontend/node_modules/*",
        "tests/*", "frontend/test/*", "frontend/e2e/*",
        "*.test.ts", "*.test.tsx", "scripts/*", "docs/*", "*.md",
        "CHANGELOG.md", "README.md", "SECURITY.md",
    )
    counts: dict[str, int] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in {".ts", ".tsx", ".py", ".html"}:
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.endswith(suffix) for suffix in excluded):
            continue
        if any(fnmatch(rel, pattern) for pattern in exclude_globs):
            continue
        if any(part in {"node_modules", ".venv", "build", "vendor", "dist", ".i18n"}
               for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # sólo literales, no comentarios
        n = 0
        for m in re.finditer(r'"([^"\\\n]*)"|\'([^\'\\\n]*)\'|`([^`\\]*)`', text):
            lit = m.group(1) or m.group(2) or m.group(3) or ""
            if CJK.search(lit) and len(lit) <= 160:
                n += 1
        if n:
            counts[rel] = n
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glossary", type=Path, default=Path("tools/i18n/glossary.zh-es.json"))
    parser.add_argument("--tree", type=Path, default=Path(".i18n/es"))
    parser.add_argument("--skip-syntax", action="store_true")
    args = parser.parse_args()

    glossary = json.loads(args.glossary.read_text(encoding="utf-8"))
    broken = check_placeholders(glossary)
    print(f"placeholders rotos: {len(broken)}")
    for item in broken[:15]:
        print(f"  {item['zh']!r} -> {item['es']!r}")
        print(f"     esperado {item['expected']} / obtenido {item['got']}")

    errors: list[str] = []
    if not args.skip_syntax and args.tree.exists():
        errors = check_syntax(args.tree)
        print(f"errores de sintaxis: {len(errors)}")
        for err in errors[:20]:
            print(f"  {err}")

    residual: dict[str, int] = {}
    if args.tree.exists():
        residual = residual_cjk(args.tree, (
            "genre_taxonomy.py", "catalog_rules.py", "kanji.py",
            "studio_sites.py", "jav-title.ts", "core/tags.ts",
        ))
        total = sum(residual.values())
        print(f"chino residual en interfaz: {total} literales en {len(residual)} archivos")
        for rel, n in sorted(residual.items(), key=lambda kv: -kv[1])[:15]:
            print(f"  {n:4d}  {rel}")

    return 1 if (broken or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
