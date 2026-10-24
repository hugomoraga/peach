"""Traducción de los mensajes de interfaz del backend al español.

La fuente sigue en el idioma de `upstream`. Cuando `PEACH_LOCALE=es`, un
middleware traduce solo los campos de interfaz de las respuestas JSON
(`message`, `detail`, `error`, ...). Los campos de datos no se tocan: una
etiqueta JAV, un género o el título de una obra no son texto de interfaz.

El modo está apagado por defecto para que los tests y la CLI sigan viendo el
texto de `upstream`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOGGER = logging.getLogger(__name__)

#: Caracteres chinos. Un texto que los trae no se da por traducido.
CJK = re.compile(r"[一-鿿㐀-䶿]")

#: Campos cuyo valor es texto para la persona que usa la app. Todo lo demás
#: se considera dato y se deja intacto.
UI_FIELDS = frozenset({
    "detail", "error", "help", "hint", "label", "message", "msg", "notice", "reason",
    "status_text", "warning",
    # Etiquetas de una fila de datos que la persona ve: el nombre del campo y
    # el texto del botón. La clave del dato (`k`, `id`, `location`) no está
    # aquí: esos valores se comparan y no se traducen.
    "term", "channel", "installation", "desktop_message", "download_label",
    # El nombre de una tarea, tal y como aparece en la lista de trabajos.
    "task_label",
    # El avance de un trabajo: la etapa, la etiqueta del paso, lo que resume el
    # resultado y el alcance de la estimación. `labels` es la lista de rótulos
    # de un volumen de disco.
    "stage", "progress_label", "eta_scope", "eta_basis", "labels",
    # Listas de descripciones de un informe: cada elemento es texto para la
    # persona, no el nombre de una columna.
    "fields",
})

#: Separadores con los que el código concatena dos textos de interfaz. El
#: separador chino se cambia por su equivalente español al componer.
COMPOSED_SEPARATORS = {"：": ": ", "、": ", ", "；": "; "}

#: Extensiones donde puede vivir el glosario, en orden de preferencia.
GLOSSARY_NAMES = (
    "tools/i18n/glossary.zh-es.json",
    "resources/i18n/glossary.zh-es.json",
    "i18n/glossary.zh-es.json",
)


def enabled() -> bool:
    value = os.environ.get("PEACH_LOCALE", "").strip().lower()
    return value == "es" or value.startswith("es-") or value == "spanish"


def _roots() -> list[Path]:
    roots = [Path(__file__).resolve().parents[2]]
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        roots.append(Path(frozen))
    return roots


@lru_cache(maxsize=1)
def glossary() -> dict[str, str]:
    explicit = os.environ.get("PEACH_I18N_GLOSSARY", "").strip()
    candidates = [Path(explicit)] if explicit else []
    for root in _roots():
        candidates.extend(root / name for name in GLOSSARY_NAMES)
    for path in candidates:
        try:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            LOGGER.warning("no se pudo leer el glosario %s: %s", path, exc)
    LOGGER.warning("modo español activo pero no se encontró el glosario; se deja el texto original")
    return {}


def translate_text(text: str) -> str:
    """Traduce un texto de interfaz.

    Primero se busca la unidad completa. Si no está, se prueban las formas
    compuestas que usa el código al concatenar dos textos ya traducibles: por
    ejemplo `f"{label}：{motivo}"` produce `本地磁盘：未配置挂载点`, que no
    existe en el glosario pero sí sus dos mitades. Solo se compone cuando
    **todas** las partes tienen traducción, así que nunca sale texto mezclado.
    """
    table = glossary()
    direct = table.get(text)
    if direct is not None:
        return direct
    for separator, spanish in COMPOSED_SEPARATORS.items():
        head, _, tail = text.partition(separator)
        if not head or not tail:
            continue
        tail_es = table.get(tail)
        if tail_es is None:
            continue
        head_es = table.get(head)
        if head_es is None:
            # La cabeza no es texto de interfaz (una marca, un número): se
            # copia tal cual, pero solo si no trae chino.
            if CJK.search(head):
                continue
            head_es = head
        # La cabeza abre la frase: en español va con mayúscula aunque el
        # glosario la guarde en minúscula por ser una etiqueta.
        head_es = head_es[:1].upper() + head_es[1:]
        return f"{head_es}{spanish}{tail_es}"
    return text


#: Script que fija el locale de react-aria antes de que carguen los bundles.
#: Sin él, selectores, calendarios y medidores usan el idioma del navegador.
LOCALE_SCRIPT = '<script>window[Symbol.for("react-aria.i18n.locale")]="es-ES";</script>'


#: Atributos cuyo valor es texto que la persona ve o lee el lector de pantalla.
HTML_TEXT_ATTRIBUTES = ("placeholder", "aria-label", "title", "alt", "aria-description")

#: Etiquetas cuyo contenido no es texto: dentro va código, no prosa.
_HTML_SKIP_TAGS = ("script", "style", "code", "pre", "svg", "textarea")


def _translate_html_attributes(html: str) -> str:
    """Traduce el valor de los atributos de interfaz que quedan en el HTML."""
    table = glossary()
    for attribute in HTML_TEXT_ATTRIBUTES:
        pattern = re.compile(rf'({attribute}=")([^"]*)(")')

        def replace(match: re.Match, table: dict[str, str] = table) -> str:
            value = match.group(2)
            if not CJK.search(value):
                return match.group(0)
            translated = table.get(value)
            if translated is None:
                return match.group(0)
            return f"{match.group(1)}{translated}{match.group(3)}"

        html = pattern.sub(replace, html)
    return html


def _translate_html_text(html: str) -> str:
    """Traduce el texto que hay entre etiquetas, fuera de los bloques de código."""
    table = glossary()
    out: list[str] = []
    position = 0
    for match in re.finditer(r"(<[^>]+>)", html):
        chunk = html[position:match.start()]
        if "<" in chunk or ">" in chunk:
            out.append(chunk)
        else:
            stripped = chunk.strip()
            translated = table.get(stripped) if stripped else None
            if translated is not None and stripped:
                lead = chunk[:len(chunk) - len(chunk.lstrip())]
                trail = chunk[len(chunk.rstrip()):]
                out.append(f"{lead}{translated}{trail}")
            else:
                out.append(chunk)
        out.append(match.group(0))
        position = match.end()
    out.append(html[position:])
    return "".join(out)


def translate_index_html(html: str) -> str:
    """Adapta la cáscara de la app (`web/index.html`) al español.

    La fuente sigue en chino: al servir se cambian el idioma del documento, el
    título, el script de react-aria y el texto que el HTML estático trae
    consigo (el buscador, los títulos de sección). Los bloques de código se
    dejan intactos: ahí dentro no hay prosa.
    """
    if not enabled():
        return html
    html = html.replace('<html lang="zh-CN"', '<html lang="es-ES"', 1)
    html = re.sub(r"<title>.*?</title>", "<title>Videodrome</title>", html, count=1, flags=re.S)
    html = _translate_html_attributes(html)
    html = _translate_html_text(html)
    if "react-aria.i18n.locale" not in html:
        html = html.replace("</head>", LOCALE_SCRIPT + "</head>", 1) if "</head>" in html else html + LOCALE_SCRIPT
    return html


def translate_payload(value: Any, field: str | None = None) -> Any:
    if isinstance(value, dict):
        # Bajo `fields` van descripciones: las claves son nombres de campo
        # (`usage`, `errors`) y los valores son el texto que se lee.
        if field == "fields":
            return {key: translate_payload(item, "fields") for key, item in value.items()}
        # Una fila con `term` es una etiqueta y su valor: ambos se leen. En
        # cualquier otra parte `value` es un dato (código, etiqueta, nombre)
        # y se deja intacto.
        if "term" in value and "value" in value:
            term, cell = value["term"], value["value"]
            return {**value,
                    "term": translate_text(term) if isinstance(term, str) else term,
                    "value": translate_text(cell) if isinstance(cell, str) else cell,
                    **{key: translate_payload(item, key)
                       for key, item in value.items()
                       if key not in {"term", "value"}}}
        return {key: translate_payload(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [translate_payload(item, field) for item in value]
    if isinstance(value, str) and field in UI_FIELDS:
        return translate_text(value)
    return value


class UiTranslationMiddleware(BaseHTTPMiddleware):
    """Traduce respuestas JSON solo cuando el modo español está activo."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not enabled():
            return response
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            payload = json.loads(body)
        except ValueError:
            return Response(
                body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        translated = json.dumps(translate_payload(payload), ensure_ascii=False).encode("utf-8")
        headers = {key: value for key, value in response.headers.items()
                   if key.lower() not in {"content-length", "content-encoding"}}
        headers["content-length"] = str(len(translated))
        return Response(
            translated,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type or "application/json",
        )
