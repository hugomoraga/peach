#!/usr/bin/env python3
"""Ensambla el glosario final desde los lotes traducidos y valida coherencia.

Salidas:
  - glossary.zh-es.json      : mapa chino -> español (el que consume translate.py)
  - conflicts.json           : cadenas traducidas de más de una forma
  - report.json              : estadísticas

Un conflicto NO es necesariamente un error: «关注» puede ser «seguir» en un
sitio y «seguimiento» en otro con sentido distinto. Lo que sí es error es que
la MISMA cadena con el MISMO sentido reciba dos traducciones. El informe los
lista para revisarlos a mano.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CJK = re.compile(r"[一-鿿㐀-䶿]")

# Palabras que en español conservan mayúscula aunque estén en línea.
KEEP_UPPER = re.compile(
    r"^(?:Videodrome|FFmpeg|FFprobe|JavDB|JavBus|DMM|MGStage|Patreon|PixPak|"
    r"CloudDrive|Clash|Telegram|Discord|HTTP|HTTPS|JSON|SQL|SQLite|API|URL|"
    r"UI|ID|MAC|OS|TT|SSS|HLS|DLNA|UPnP|SQL|FTS5|WebP|MP4|MKV|AV1|HEVC|"
    r"AV1|H\.264|H\.265|AAC|FLAC|PCM|NFO|TS|M2TS|MKV|WebM|MP3)"
)


def normalize_case(text: str) -> str:
    """Ajusta la caja inicial según si la cadena es una etiqueta o una frase.

    - Etiqueta corta (<= 15 caracteres): minúscula ("buscar", "descargar").
    - Frase larga: primera letra mayúscula ("La operación falló...").
    - Si empieza por un placeholder o un símbolo, no se toca.
    - Siglas y nombres propios conservan su caja.
    """
    if not text:
        return text
    if KEEP_UPPER.match(text):
        return text
    if len(text) > 1 and text[1].isupper():
        # "MP4", "MKV", "SD"… ya es sigla o CamelCase: se respeta
        return text
    if text[0] in "${([«¿-—…":
        # empieza por placeholder o signo: la caja la decide el autor original
        return text
    if len(text) <= 15:
        # etiqueta corta: minúscula
        return text[0].lower() + text[1:]
    # frase larga: capital inicial
    return text[0].upper() + text[1:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches", type=Path, default=Path("tools/i18n/out"))
    parser.add_argument("--extra", type=Path, default=Path("tools/i18n/pendout"),
                        help="carpeta con lotes adicionales (pendientes)")
    parser.add_argument("--out", type=Path, default=Path("tools/i18n/glossary.zh-es.json"))
    parser.add_argument("--report", type=Path, default=Path("tools/i18n/report.json"))
    parser.add_argument("--seed", type=Path, default=Path("tools/i18n/seed-glossary.json"))
    parser.add_argument("--manual", type=Path, default=Path("tools/i18n/manual-glossary.json"),
                        help="glosario con traducciones hechas a mano")
    parser.add_argument("--manual2", type=Path, default=Path("tools/i18n/manual-glossary-2.json"),
                        help="segundo glosario manual")
    parser.add_argument("--manual3", type=Path, default=Path("tools/i18n/manual-glossary-3.json"),
                        help="tercer glosario manual")
    parser.add_argument("--manual4", type=Path, default=Path("tools/i18n/manual-glossary-4.json"),
                        help="cuarto glosario manual")
    parser.add_argument("--manual5", type=Path, default=Path("tools/i18n/manual-glossary-5.json"),
                        help="quinto glosario manual")
    parser.add_argument("--manual6", type=Path, default=Path("tools/i18n/manual-glossary-6.json"),
                        help="sexto glosario manual")
    parser.add_argument("--manual7", type=Path, default=Path("tools/i18n/manual-glossary-7.json"),
                        help="séptimo glosario manual")
    parser.add_argument("--manual8", type=Path, default=Path("tools/i18n/manual-glossary-8.json"),
                        help="octavo glosario manual")
    parser.add_argument("--manual9", type=Path, default=Path("tools/i18n/manual-glossary-9.json"),
                        help="noveno glosario manual")
    parser.add_argument("--manual10", type=Path, default=Path("tools/i18n/manual-glossary-10.json"),
                        help="décimo glosario manual; además de `terms`, admite `exclude`")
    parser.add_argument("--base", type=Path, default=Path("tools/i18n/glossary.zh-es.json"),
                        help="glosario anterior; sus entradas sobreviven si no hay una traducción nueva")
    args = parser.parse_args()

    # Semilla canónica: gana sobre cualquier traducción de lote.
    glossary: dict[str, str] = {}
    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    for zh, es in seed.get("terms", {}).items():
        if es:
            glossary[zh] = es

    # Glosario manual: traducciones hechas a mano, con prioridad sobre los
    # lotes automáticos.
    if args.manual.exists():
        manual = json.loads(args.manual.read_text(encoding="utf-8"))
        for zh, es in manual.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual2.exists():
        manual2 = json.loads(args.manual2.read_text(encoding="utf-8"))
        for zh, es in manual2.get("terms", {}).items():
            if es:
                glossary[zh] = es

    # Cada cadena traducida aporta una variante. La semilla canónica es la
    # que gana cuando hay discrepancia: es la decisión ya revisada.
    seed_terms = seed.get("terms", {})
    variants: dict[str, set[str]] = defaultdict(set)
    translated = 0
    untranslated: dict[str, list[str]] = defaultdict(list)
    batches = sorted(args.batches.glob("batch_*.json"))
    if args.extra.exists():
        batches += sorted(args.extra.glob("pend_*.json"))
    for path in batches:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"AVISO: {path.name} ilegible: {exc}")
            continue
        for item in data.get("items", []):
            zh = item.get("zh", "")
            es = item.get("es", "")
            if not zh or not CJK.search(zh):
                continue
            if not es:
                untranslated[zh].append(path.name)
                continue
            translated += 1
            variants[zh].add(es)

    conflicts = {
        zh: sorted(vals)
        for zh, vals in variants.items()
        if len(vals) > 1
    }

    # Los conflictos que sólo difieren en caja no son conflictos reales.
    real_conflicts = {}
    for zh, vals in conflicts.items():
        folded = {v[:1].lower() + v[1:] for v in vals}
        if len(folded) > 1:
            real_conflicts[zh] = sorted(vals)

    # Glosario final: se parte del anterior para no perder traducciones cuando
    # esta pasada solo cubre las cadenas nuevas. Después, la semilla y el
    # manual mandan; si no hay decisión canónica, se toma la variante del lote.
    glossary: dict[str, str] = {}
    if args.base.exists():
        glossary.update(json.loads(args.base.read_text(encoding="utf-8")))
    for zh, vals in variants.items():
        if zh in seed_terms and seed_terms[zh]:
            glossary[zh] = seed_terms[zh]
        else:
            glossary[zh] = sorted(vals)[0]
    # La semilla y el manual pueden traer términos que aún no aparecen en los
    # lotes (por ejemplo, texto JSX que el extractor no recogió).
    for zh, es in seed_terms.items():
        if es and zh not in glossary:
            glossary[zh] = es
    if args.manual.exists():
        manual = json.loads(args.manual.read_text(encoding="utf-8"))
        for zh, es in manual.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual2.exists():
        manual2 = json.loads(args.manual2.read_text(encoding="utf-8"))
        for zh, es in manual2.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual3.exists():
        manual3 = json.loads(args.manual3.read_text(encoding="utf-8"))
        for zh, es in manual3.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual4.exists():
        manual4 = json.loads(args.manual4.read_text(encoding="utf-8"))
        for zh, es in manual4.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual5.exists():
        manual5 = json.loads(args.manual5.read_text(encoding="utf-8"))
        for zh, es in manual5.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual6.exists():
        manual6 = json.loads(args.manual6.read_text(encoding="utf-8"))
        for zh, es in manual6.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual7.exists():
        manual7 = json.loads(args.manual7.read_text(encoding="utf-8"))
        for zh, es in manual7.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual8.exists():
        manual8 = json.loads(args.manual8.read_text(encoding="utf-8"))
        for zh, es in manual8.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual9.exists():
        manual9 = json.loads(args.manual9.read_text(encoding="utf-8"))
        for zh, es in manual9.get("terms", {}).items():
            if es:
                glossary[zh] = es
    if args.manual10.exists():
        manual10 = json.loads(args.manual10.read_text(encoding="utf-8"))
        for zh, es in manual10.get("terms", {}).items():
            if es:
                glossary[zh] = es
        # `exclude` quita entradas: son valores que se guardan o se comparan
        # (bandas de duración, sufijos de recuento) y traducirlos rompería los
        # datos que ya están en la base.
        for zh in manual10.get("exclude", []):
            glossary.pop(zh, None)

    for zh in list(glossary):
        glossary[zh] = normalize_case(glossary[zh])

    args.out.write_text(
        json.dumps(glossary, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )

    report = {
        "batches": len(batches),
        "translated": translated,
        "glossary_entries": len(glossary),
        "untranslated_count": len(untranslated),
        "untranslated": {k: v[:2] for k, v in sorted(untranslated.items())},
        "conflicts": real_conflicts,
        "conflict_count": len(real_conflicts),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"lotes: {len(batches)}")
    print(f"traducidas: {translated}")
    print(f"glosario: {len(glossary)} entradas -> {args.out}")
    print(f"sin traducir: {len(untranslated)}")
    print(f"conflictos: {len(conflicts)} -> ver {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
