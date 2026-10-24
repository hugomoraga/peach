#!/usr/bin/env python3
"""Comprueba los enlaces del README: rutas internas y URLs externas.

- Ruta interna: el archivo tiene que existir.
- Ancla interna: el título tiene que existir en el archivo (GitHub genera el
  anchor a partir del título, en minúsculas y con los espacios en guiones).
- URL externa: responde algo distinto de 404.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

README = Path(__import__("os").environ.get("README","README.md"))


def slug(title: str) -> str:
    """El anchor que GitHub genera para un encabezado Markdown."""
    s = title.strip().lower()
    s = re.sub(r"[`*_~]", "", s)
    # GitHub quita la puntuación pero conserva los caracteres CJK
    s = re.sub(r"[^\w\s\-À-ɏ一-鿿]", "", s)
    return re.sub(r"\s+", "-", s)


def anchors_in(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists() or path.suffix != ".md":
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if m:
            out.add(slug(m.group(2)))
    return out


def check_external(url: str) -> str:
    try:
        req = Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=20) as r:
            return "ok" if r.status < 400 else f"HTTP {r.status}"
    except HTTPError as e:
        return f"HTTP {e.code}"
    except URLError as e:
        return f"sin red: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def main() -> int:
    text = README.read_text(encoding="utf-8")
    problems: list[str] = []

    # Enlaces markdown [texto](destino) e <img src="...">
    targets = re.findall(r"\]\(([^)\s]+)\)", text)
    targets += re.findall(r'src="([^"]+)"', text)
    targets += re.findall(r'href="([^"]+)"', text)

    seen: set[str] = set()
    for t in targets:
        if t in seen:
            continue
        seen.add(t)
        if t.startswith("#"):
            if slug(t[1:]) not in anchors_in(README) and t[1:].lower() not in {
                slug(h) for h in re.findall(r"^#{1,6}\s+(.*)$", text, re.M)
            }:
                problems.append(f"ancla interna rota: {t}")
            continue
        if t.startswith(("http://", "https://")):
            continue
        path_part, _, anchor = t.partition("#")
        target = Path(path_part)
        if not target.exists():
            problems.append(f"archivo no existe: {t}")
        elif anchor:
            if anchor not in anchors_in(target):
                problems.append(f"ancla rota: {t}  (anchors: {sorted(anchors_in(target))[:6]}...)")

    print(f"enlaces revisados: {len(seen)}")
    if problems:
        print("PROBLEMAS:")
        for p in problems:
            print("  -", p)
    else:
        print("todos los enlaces internos resuelven")

    # Ahora las URLs externas (solo las de imágenes y enlaces del README).
    external = sorted({t for t in seen if t.startswith(("http://", "https://"))})
    print(f"\nURLs externas ({len(external)}):")
    for url in external:
        status = check_external(url)
        flag = "" if status == "ok" else "   <-- revisar"
        print(f"  {status:12} {url}{flag}")
        if status != "ok":
            problems.append(f"URL rota: {url} ({status})")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
