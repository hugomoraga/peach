#!/usr/bin/env python3
"""Extrae literales con CJK del frontend y del backend, con su ubicación.

El frontend se escanea con `tools/i18n/jsstrings.py`, que entiende las
plantillas JS con interpolaciones anidadas (un regex no llega).

El backend se escanea con `tokenize`, que ya entrega el literal completo.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402
from translate import CODE_MARKERS  # noqa: E402

CJK = re.compile(r"[一-鿿㐀-䶿]")
MAX_LEN = 300


JSX_TEXT = re.compile(r">([^<>{}]+)<")


def frontend_literals(root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for lit in scan_js(text):
            body = lit.body
            if not CJK.search(body) or len(body) > MAX_LEN:
                continue
            line = text.count("\n", 0, lit.start) + 1
            found.setdefault(body, []).append(f"{rel}:{line}")
        # texto contenido entre etiquetas JSX: `<Button>登录</Button>`
        if path.suffix in {".tsx", ".jsx"}:
            for match in JSX_TEXT.finditer(text):
                body = match.group(1).strip()
                if not CJK.search(body) or len(body) > MAX_LEN:
                    continue
                # Entre `>` y `<` también hay código: comparadores, genéricos,
                # ternarios y comentarios. Esos tramos no son interfaz.
                if CODE_MARKERS.search(body) or any(mark in body for mark in ("/*", "*/", "?", ":", "/>")):
                    continue
                line = text.count("\n", 0, match.start(1)) + 1
                found.setdefault(body, []).append(f"{rel}:{line}")
    return found


def python_literals(root: Path) -> dict[str, list[str]]:
    """Literales de texto del backend, sin docstrings.

    `tokenize` confunde un docstring de módulo con un literal normal cuando va
    precedido de un comentario o de la declaración de codificación. El AST sí
    sabe cuál es un docstring, así que la cobertura no cuenta prosa de
    documentación como si fuera interfaz.
    """
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
            # Los trozos de un f-string son fragmentos de un mensaje, no la
            # unidad que se traduce: se cuentan cuando la plantilla entera
            # aparezca como literal, no aquí.
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                for part in node.values:
                    if isinstance(part, ast.Constant):
                        docstrings.add(id(part))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings:
                continue
            value = node.value
            if CJK.search(value) and len(value) <= MAX_LEN * 2:
                found.setdefault(value, []).append(f"{rel}:{node.lineno}")
    return found


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    fe = frontend_literals(root / "frontend" / "src")
    py = python_literals(root / "src")
    # Los tests también comparan contra texto de interfaz: sus literales van
    # al glosario igual que los de la app, para que `tr()` los resuelva.
    tests = frontend_literals(root / "frontend" / "test")
    payload = {"frontend": fe, "python": py, "tests": tests}
    out = Path(__file__).resolve().parent / "glossary_source.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"frontend literals: {len(fe)}  chars={sum(len(k) for k in fe)}")
    print(f"python literals:   {len(py)}  chars={sum(len(k) for k in py)}")
    print(f"test literals:     {len(tests)}  chars={sum(len(k) for k in tests)}")
    print(f"written -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
