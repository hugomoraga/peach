#!/usr/bin/env python3
"""Escáner de literales de JavaScript/TypeScript.

Un regex no sirve: las plantillas `` ` `` pueden contener otros backticks
dentro de expresiones `${...}`, y las cadenas pueden contener comillas
opuestas sin problema. Ejemplo real del proyecto:

    `${active.from}${active.ongoing ? ' – 至今' : active.to ? ` – ${active.to}` : ''}`

Un regex `` `([^`]*)` `` corta en el backtick interno y devuelve una cadena
incompleta, que luego no encuentra su par en el glosario y deja el original
sin traducir.

Este módulo devuelve literales COMPLETOS con su delimitador y su contenido.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Literal:
    start: int      # índice del delimitador de apertura
    end: int        # índice DESPUÉS del delimitador de cierre
    quote: str      # '"', "'" o '`'
    body: str       # contenido sin el delimitador

    @property
    def raw(self) -> str:
        return self.body


def scan(text: str) -> list[Literal]:
    """Devuelve todos los literales de cadena del código."""
    out: list[Literal] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'`":
            lit = _scan_literal(text, i, ch)
            if lit is None:
                i += 1
                continue
            out.append(lit)
            i = lit.end
            continue
        # comentarios: se saltan enteros
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                j = text.find("\n", i)
                i = n if j < 0 else j + 1
                continue
            if nxt == "*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
        i += 1
    return out


def _scan_literal(text: str, start: int, quote: str) -> Literal | None:
    """Escanea un literal que empieza en `start` con el delimitador `quote`."""
    n = len(text)
    i = start + 1
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return Literal(start=start, end=i + 1, quote=quote, body=text[start + 1 : i])
        if quote == "`" and ch == "$" and i + 1 < n and text[i + 1] == "{":
            # expresión interpolada: hay que balancear las llaves y saltar el
            # contenido, que puede contener sus propios literales y backticks
            j = _skip_interpolation(text, i + 1)
            if j < 0:
                return None
            i = j
            continue
        i += 1
    return None  # literal sin cerrar: no es un literal


def _skip_interpolation(text: str, brace_start: int) -> int:
    """Devuelve el índice justo después del `}` que cierra `${`.

    Dentro se ignoran los literales (pueden contener llaves) y se cuentan
    las llaves reales.
    """
    n = len(text)
    depth = 0
    i = brace_start
    while i < n:
        ch = text[i]
        if ch in "\"'`":
            lit = _scan_literal(text, i, ch)
            if lit is None:
                return -1
            i = lit.end
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def mask_non_code(text: str) -> str:
    """Rellena con espacios todo lo que NO es código: comentarios.

    Conserva longitud y saltos de línea, así los índices siguen valiendo.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            end = n if j < 0 else j
            for k in range(i, end):
                out[k] = " "
            i = end
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            end = n if j < 0 else j + 2
            for k in range(i, end):
                if text[k] != "\n":
                    out[k] = " "
            i = end
            continue
        if ch in "\"'`":
            lit = _scan_literal(text, i, ch)
            if lit is None:
                i += 1
                continue
            i = lit.end
            continue
        i += 1
    return "".join(out)
