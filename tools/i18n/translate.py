#!/usr/bin/env python3
"""Aplica el glosario zh→es sobre el árbol de fuentes de Peach.

Por qué un codemod y no edición directa: el upstream upstream/master avanza en
chino. Si se editan los archivos a mano, cada merge upstream vuelve a chocar
sobre los mismos archivos traducidos. Con este script el árbol de fuentes queda
en chino (los merges son limpios) y la traducción se aplica sobre una COPIA
durante el build. Actualizar upstream = mergear + volver a correr el script.

Uso:
    tools/i18n/translate.py --src . --out .i18n/es --glossary tools/i18n/glossary.zh-es.json

Reglas de reemplazo:
- Coincidencia exacta del literal completo: prioridad máxima.
- Si no hay coincidencia exacta, se buscan las claves más largas contenidas
  dentro del literal (caso de plantillas con interpolación: "共 ${n} 项").
- Las claves de datos (etiquetas JAV, géneros, kanji) no están en el glosario:
  se dejan intactas a propósito, porque son la verdad de la base de datos.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsstrings import scan as scan_js  # noqa: E402

CJK = re.compile(r"[一-鿿㐀-䶿]")

# Literales de una línea y plantillas. El orden importa: primero el literal
# completo, después los prefijos largos.
TS_LITERAL = re.compile(
    r'"((?:[^"\\\n]|\\.)*)"'      # dobles
    r"|'((?:[^'\\\n]|\\.)*)'"     # simples
    r"|`((?:[^`\\]|\\.)*)`",       # plantillas (sin saltos de línea)
    re.S,
)

# Archivos que NO se traducen: su chino es el valor real que se guarda en la
# base de datos o se compara contra fuentes japonesas. Traducirlos rompería el
# matching de etiquetas y géneros.
# Se comparan por SUFIJO: las rutas reales son relativas a src/ o frontend/src/.
EXCLUDE_SUFFIXES = (
    "genre_taxonomy.py",
    "catalog_rules.py",
    "kanji.py",
    "studio_sites.py",
    "jav-title.ts",
    "core/tags.ts",
)

EXCLUDE_GLOBS = (
    "tools/i18n/*",
    "tools/extract_strings.py",
    # El propio traductor contiene patrones en chino que no son interfaz.
    "src/peach/ui_translation.py",
    "peach/ui_translation.py",
    # dependencias de terceros: su idioma es responsabilidad de ellas
    "web/vendor/*",
    "web/dist/*",
    "frontend/node_modules/*",
    # las pruebas comparan literales exactos: traducirlos rompe las aserciones
    "tests/*",
    "frontend/test/*",
    "frontend/e2e/*",
    "*.test.ts",
    "*.test.tsx",
    # herramientas de desarrollo: su salida es para quien programa, no para
    # quien usa la app
    "scripts/*",
    # documentación: no es interfaz
    "docs/*",
    "*.md",
    "CHANGELOG.md",
    "README.md",
    "SECURITY.md",
    "*.po",
    "*.pot",
)

TEXT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".html", ".css", ".md"}


def excluded(rel: str) -> bool:
    from fnmatch import fnmatch

    if any(rel.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return True
    return any(fnmatch(rel, pattern) for pattern in EXCLUDE_GLOBS)


def mask_comments_ts(text: str) -> str:
    """Devuelve el texto con los comentarios rellenados de espacios.

    Conserva longitud y saltos de línea, así los desfases siguen valiendo.
    """
    out = list(text)
    i = 0
    n = len(text)
    state = None  # None | 'line' | 'block' | '"' | "'" | '`'
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state is None:
            if ch == "/" and nxt == "/":
                state = "line"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch in "\"'`":
                state = ch
            i += 1
            continue
        if state == "line":
            if ch == "\n":
                state = None
            else:
                out[i] = " "
            i += 1
            continue
        if state == "block":
            if ch == "*" and nxt == "/":
                out[i] = out[i + 1] = " "
                state = None
                i += 2
                continue
            if ch != "\n":
                out[i] = " "
            i += 1
            continue
        # dentro de una cadena: se sale en la comilla sin escapar
        if ch == "\\":
            i += 2
            continue
        if ch == state:
            state = None
        i += 1
    return "".join(out)


def longest_first(glossary: dict[str, str]) -> list[tuple[str, str]]:
    return sorted(glossary.items(), key=lambda kv: (-len(kv[0]), kv[0]))


MAX_SUBSTITUTION_LEN = 24

# Señales de que un fragmento capturado entre `>` y `<` es código, no texto
# de interfaz: el operador `=>`, los comparadores, las llamadas, los
# genéricos. Sin este filtro, `a > b && c < d` parece un literal JSX.
CODE_MARKERS = re.compile(
    r"=>|&&|\|\||\bfunction\b|\bconst\b|\breturn\b|\bimport\b|"
    r"[A-Za-z_$][\w$]*\s*\([^)]*\)\s*[;{]|"
    r"[<>]=|===|!==|\.\w+\s*\("
)

# Conectores y puntuación que delatan una FRASE (no una etiqueta).
# Si aparecen, la cadena es texto corrido y no se sustituye pieza a pieza.
PHRASE_MARKERS = "，。、；：？！…（）《》“”‘’·—"


def _is_short_label(text: str) -> bool:
    """True si la cadena es una etiqueta corta, apta para sustitución.

    Criterio: sin conectores de frase, corta, y con pocos caracteres CJK.
    "已装上" (3 CJK) es etiqueta. "端口正en使用" (5 CJK) es frase corta y NO
    debe sustituirse: "en" y "ninguno" vienen de sustituciones parciales de
    claves como "正在使用" y "无".
    """
    if any(marker in text for marker in PHRASE_MARKERS):
        return False
    cjk = len(CJK.findall(text))
    if cjk > 6:
        return False
    if len(text) > MAX_SUBSTITUTION_LEN:
        return False
    return True


def translate_literal(text: str, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[str, bool]:
    """Traduce el contenido de un literal. Devuelve (texto, cambió).

    1. Coincidencia exacta del literal completo: es el camino normal y el
       que produce texto natural. Cubre la mayoría de los casos.

    2. Sustitución dentro de una interpolación: `${x ? '甲' : '乙'}` lleva
       el texto chino entre comillas dentro de la plantilla. Ahí la clave ES
       el texto a traducir y se puede sustituir sin riesgo: el delimitador
       sigue siendo el mismo y la expresión no se rompe.

    Lo que NO se hace es trocear la cadena y reemplazar por partes: "端口正在
    使用" se convertiría en "端口正en使用", porque "在" está dentro de la
    clave "正在使用" y "使用" dentro de "无". Mezclar idiomas es peor que
    dejar la cadena en chino, que al menos es legible.
    """
    if not CJK.search(text):
        return text, False
    exact = glossary.get(text)
    if exact is not None:
        return exact, exact != text

    result = text
    changed = False
    taken: list[tuple[int, int]] = []

    def overlaps(pos: int, end: int) -> bool:
        return any(not (end <= s or pos >= e) for s, e in taken)

    # Sustitución del texto chino que aparece entre comillas dentro de la
    # cadena: es el caso de las interpolaciones condicionales.
    for key, value in ordered:
        if not CJK.search(key):
            continue
        for quote in ("'", '"', "`"):
            pattern = quote + key + quote
            start = 0
            while True:
                pos = result.find(pattern, start)
                if pos < 0:
                    break
                end = pos + len(pattern)
                if not overlaps(pos, end):
                    taken.append((pos, end))
                    # se conserva el delimitador que tenía el original:
                    # un atributo HTML con comillas dobles no puede pasar a
                    # comillas simples sin romper la expresión que lo contiene
                    result = result[:pos] + quote + value + quote + result[end:]
                    changed = True
                    start = pos + len(value) + 2
                else:
                    start = pos + 1

    return result, changed


def _is_expr_char(ch: str) -> bool:
    """Caracteres que indican que la clave forma parte de una expresión JS."""
    return ch in "$`'\"()[]{}<>=+-*/%?:!,.;&|"


def _translate_segment(seg: str, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[str, bool]:
    """Traduce un tramo de texto, tolerando el espacio que lo rodea.

    El codemod hace coincidencia EXACTA: sin eso, trocear "端口正在使用"
    produciría "端口正en使用". Pero los tramos de JSX y de atributos HTML
    llegan con el espacio que los separa de la interpolación: " 部有编号作品、"
    no es la misma clave que "部有编号作品、".

    Aquí se intenta primero el tramo tal cual y, si no hay coincidencia, el
    mismo tramo sin los espacios del borde. El espacio se vuelve a poner
    después: solo cambia el texto, no la estructura.
    """
    if not CJK.search(seg):
        return seg, False
    new_seg, changed = translate_literal(seg, glossary, ordered)
    if changed:
        return new_seg, True
    stripped = seg.strip()
    if stripped and stripped != seg:
        new_stripped, changed = translate_literal(stripped, glossary, ordered)
        if changed:
            lead = seg[: len(seg) - len(seg.lstrip())]
            trail = seg[len(seg.rstrip()) :]
            return lead + new_stripped + trail, True
    return seg, False


def translate_jsx_text(path: Path, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[int, list[str]]:
    """Traduce el texto contenido entre etiquetas JSX.

    `<Button>登录</Button>` no es un literal: es el contenido de un elemento.
    Estos textos son tan UI como los literales, y en el login/setup son la
    mayor parte de lo visible.

    El texto puede además estar partido por interpolaciones:

        >已经导入了 {n} 份浏览器历史。<

    Ahí se traduce cada tramo por separado: el de antes de la expresión, el
    de después.

    CUIDADO con qué se considera "texto": entre `>` y `<` puede haber
    código JS (ternarios, llamadas, comentarios). El patrón anterior
    (`>([^<>]+)<`) se comía el `: null}载入更多` de
    `{busy ? <span/> : null}载入更多</Button>` y rompía el JSX.

    Ahora sólo se traduce un tramo si:
      - no contiene `{` ni `}` (no es una expresión ni un bloque),
      - no contiene `/>` (no cruza un tag auto-cerrado),
      - no contiene `?` ni `:` de ternario,
      - no contiene `/*` (no es un comentario).
    """
    text = path.read_text(encoding="utf-8")
    edits: list[tuple[int, int, str]] = []
    missed: list[str] = []
    pattern = re.compile(r">([^<>]+)<")
    for match in pattern.finditer(text):
        body = match.group(1)
        if not CJK.search(body):
            continue
        # `>` y `<` también aparecen en el código: el operador `=>`, los
        # genéricos, los comparadores. Lo que se atrapa así no es texto de
        # interfaz y no se debe traducir.
        if CODE_MARKERS.search(body):
            continue
        # Los comentarios JSX `{/* ... */}` no son texto de interfaz.
        if "/*" in body or "*/" in body:
            continue
        # El cuerpo puede contener interpolaciones `{...}`: se dividen en
        # tramos y se traduce sólo el texto.
        #
        # Un ternario (`a ? b : c`) sí es código, no texto.
        if "?" in body or ":" in body:
            continue
        # Un tag auto-cerrado dentro del cuerpo significa que el emparejamiento
        # cruzó una frontera de elemento: el texto no es contiguo.
        if "/>" in body:
            continue
        # Divide el contenido en tramos de texto y expresiones `{...}`.
        segments = re.split(r"(\{[^{}]*\})", body)
        changed_any = False
        new_segments: list[str] = []
        for seg in segments:
            if not CJK.search(seg):
                new_segments.append(seg)
                continue
            # Un tramo que es una expresión pura (`{job.message}`) no es texto.
            if seg.startswith("{") and seg.endswith("}"):
                new_segments.append(seg)
                continue
            new_seg, changed = _translate_segment(seg, glossary, ordered)
            if changed:
                changed_any = True
                new_segments.append(new_seg)
            else:
                new_segments.append(seg)
                missed.append(seg)
        if not changed_any:
            continue
        new_body = "".join(new_segments)
        edits.append((match.start(1), match.end(1), new_body))
    if not edits:
        return 0, missed
    out = text
    for start, end, replacement in sorted(edits, reverse=True):
        out = out[:start] + replacement + out[end:]
    path.write_text(out, encoding="utf-8")
    return len(edits), missed


def translate_html_attrs(path: Path, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[int, list[str]]:
    """Traduce el texto de los atributos HTML dentro de plantillas.

    '<button title="永久删除回收站内容">清空回收站</button>'

    El valor del atributo es texto visible (el title es el tooltip), pero no
    es un literal JS ni JSX entre tags: está dentro de comillas dobles.
    """
    text = path.read_text(encoding="utf-8")
    edits: list[tuple[int, int, str]] = []
    missed: list[str] = []
    pattern = re.compile(
        r'(title|alt|aria-label|placeholder|data-initial|data-placeholder)="([^"]*)"'
    )
    for match in pattern.finditer(text):
        value = match.group(2)
        if not CJK.search(value):
            continue
        segments = re.split(r"(\{[^{}]*\})", value)
        changed_any = False
        new_segments: list[str] = []
        for seg in segments:
            if not CJK.search(seg):
                new_segments.append(seg)
                continue
            new_seg, changed = _translate_segment(seg, glossary, ordered)
            if changed:
                changed_any = True
                new_segments.append(new_seg)
            else:
                new_segments.append(seg)
                missed.append(seg)
        if not changed_any:
            continue
        new_value = "".join(new_segments)
        edits.append((match.start(2), match.end(2), new_value))
    if not edits:
        return 0, missed
    out = text
    for start, end, replacement in sorted(edits, reverse=True):
        out = out[:start] + replacement + out[end:]
    path.write_text(out, encoding="utf-8")
    return len(edits), missed


def translate_ts(path: Path, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    edits: list[tuple[int, int, str]] = []
    missed: list[str] = []
    for lit in scan_js(text):
        body = lit.body
        if not CJK.search(body):
            continue
        new_body, changed = translate_literal(body, glossary, ordered)
        if not changed:
            missed.append(body)
            continue
        quote = lit.quote
        if quote == '"':
            escaped = new_body.replace("\\", "\\\\").replace('"', '\\"')
        elif quote == "'":
            escaped = new_body.replace("\\", "\\\\").replace("'", "\\'")
        else:
            # Dentro de una plantilla no se escapan los backticks: los que
            # ya venían escapados en el original conservan su escape, y los
            # que aparecen sin escapar son backticks anidados que el
            # analizador de TS/JSX resuelve por su cuenta. Escaparlos rompe
            # la expresión.
            escaped = new_body
        edits.append((lit.start, lit.end, quote + escaped + quote))
    jsx_count = 0
    jsx_missed: list[str] = []
    if edits:
        out = text
        for start, end, replacement in sorted(edits, reverse=True):
            out = out[:start] + replacement + out[end:]
        path.write_text(out, encoding="utf-8")
        text = out
    if path.suffix in {".tsx", ".jsx", ".ts", ".js"}:
        jsx_count, jsx_missed = translate_jsx_text(path, glossary, ordered)
        attr_count, attr_missed = translate_html_attrs(path, glossary, ordered)
        jsx_count += attr_count
        jsx_missed.extend(attr_missed)
    total = len(edits) + jsx_count
    missed.extend(jsx_missed)
    return total, missed


def translate_python(path: Path, glossary: dict[str, str], ordered: list[tuple[str, str]]) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    with path.open("rb") as raw:
        tokens = list(tokenize.tokenize(raw.readline))
    edits: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    missed: list[str] = []
    for tok in tokens:
        if tok.type != tokenize.STRING:
            continue
        raw_text = tok.string
        prefix_len = len(raw_text) - len(raw_text.lstrip("rRbBuUfF"))
        prefix = raw_text[:prefix_len]
        quote_char = raw_text[prefix_len]
        is_docstring = quote_char in "\"'" and raw_text[prefix_len : prefix_len + 3] == quote_char * 3
        if is_docstring:
            # Los docstrings son documentación del código, no interfaz de
            # usuario: no se traducen. Traducirlos además rompe el archivo,
            # porque el texto puede contener comillas triples.
            continue
        try:
            value = ast.literal_eval(raw_text)
        except Exception:
            continue
        if not isinstance(value, str) or not CJK.search(value):
            continue
        new_value, changed = translate_literal(value, glossary, ordered)
        if not changed:
            missed.append(value)
            continue
        if "\n" in new_value:
            # Una traducción con salto de línea no cabe en un literal de una
            # sola línea: el original era multilínea y su escapado es
            # distinto. Se deja sin traducir y se reporta.
            missed.append(value)
            continue
        quote = quote_char
        if quote not in "\"'":
            quote = '"'
        body = new_value.replace("\\", "\\\\").replace(quote, "\\" + quote)
        new_literal = f"{prefix}{quote}{body}{quote}"
        edits.append((tok.start, tok.end, new_literal))
    if not edits:
        return 0, missed
    lines = text.splitlines(keepends=True)
    # posiciones en columnas -> offsets absolutos
    offsets = []
    acc = 0
    for line in lines:
        offsets.append(acc)
        acc += len(line)
    out = text
    for (srow, scol), (erow, ecol), literal in sorted(edits, reverse=True):
        start = offsets[srow - 1] + scol
        end = offsets[erow - 1] + ecol
        out = out[:start] + literal + out[end:]
    path.write_text(out, encoding="utf-8")
    return len(edits), missed


def copy_tree(src: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    ignore = shutil.ignore_patterns(
        ".git", "node_modules", ".venv", "build", "dist", "__pycache__",
        ".i18n", ".pytest_cache", "*.pyc",
    )
    shutil.copytree(src, out, ignore=ignore, symlinks=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path(".i18n/es"))
    parser.add_argument("--glossary", type=Path, default=Path("tools/i18n/glossary.zh-es.json"))
    parser.add_argument("--report", type=Path, default=Path("tools/i18n/report.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="traduce el árbol de --src directamente, sin copiar",
    )
    args = parser.parse_args()

    src = args.src.resolve()
    out = args.out.resolve()
    glossary = json.loads(args.glossary.read_text(encoding="utf-8"))
    ordered = longest_first(glossary)

    if args.in_place:
        out = src
    else:
        copy_tree(src, out)

    total = 0
    missed: dict[str, list[str]] = {}
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(out).as_posix()
        if excluded(rel):
            continue
        if path.suffix == ".py":
            count, missing = translate_python(path, glossary, ordered)
        else:
            count, missing = translate_ts(path, glossary, ordered)
        if count:
            total += count
            print(f"  {count:4d}  {rel}")
        for item in missing:
            missed.setdefault(item, []).append(rel)

    report = {
        "glossary_entries": len(glossary),
        "replacements": total,
        "untranslated": {k: v[:3] for k, v in sorted(missed.items())},
        "untranslated_count": len(missed),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nreemplazos: {total}")
    print(f"sin traducir: {len(missed)}")
    print(f"informe -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
