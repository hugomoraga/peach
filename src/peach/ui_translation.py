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


def translate_index_html(html: str) -> str:
    """Adapta la cáscara de la app (`web/index.html`) al español.

    La fuente sigue en chino: el idioma del documento, el título y el script de
    react-aria se cambian al servir. No se tocan datos ni el resto del marcado.
    """
    if not enabled():
        return html
    html = html.replace('<html lang="zh-CN"', '<html lang="es-ES"', 1)
    html = html.replace("<title>Peach · 蜜桃</title>", "<title>Peach</title>", 1)
    html = html.replace("跳到正文", "Saltar al contenido")
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
