#!/usr/bin/env bash
# Compila el frontend en español sin tocar la fuente versionada.
#
# El pipeline vive en `build_frontend.py`: copia a `.i18n/es/`, traduce la
# copia, compila y publica `web/dist/`. Este script solo elige el intérprete y,
# si se pide, empaqueta después.
#
# Uso:
#   tools/i18n/build_es.sh            # frontend -> web/dist
#   tools/i18n/build_es.sh --package  # además empaqueta la app macOS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
if [[ -z "$PY" ]]; then
  echo "No hay Python 3.11+ para ejecutar el pipeline." >&2
  exit 1
fi

"$PY" tools/i18n/build_frontend.py --repo "$ROOT"

if [[ "${1:-}" == "--package" ]]; then
  "$PY" -X utf8 scripts/build_macos_standalone.py --no-dmg --target-arch arm64
fi

echo "LISTO: web/dist compilado en español; la fuente sigue en el idioma de upstream."
