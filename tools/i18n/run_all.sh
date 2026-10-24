#!/usr/bin/env bash
# Traduce todos los lotes con OpenCode, N en paralelo.
# Uso: run_all.sh [paralelo] [modelo]
set -uo pipefail

PARALLEL="${1:-6}"
MODEL="${2:-opencode/big-pickle}"
# El repo se deduce de donde está este script: la ruta depende de dónde se
# clonó y no puede ir escrita en el archivo.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.opencode/bin:$PATH"

BATCH_DIR="tools/i18n/batches"
OUT_DIR="tools/i18n/out"
mkdir -p "$OUT_DIR"

run_one() {
  local batch="$1"
  local name
  name="$(basename "$batch" .json)"
  local out="$OUT_DIR/$name.json"
  if [ -s "$out" ] && python3 -c "
import json,sys
d=json.load(open('$out'))
sys.exit(0 if 'items' in d else 1)
" 2>/dev/null; then
    echo "SKIP $name (ya existe)"
    return 0
  fi
  if ./tools/i18n/translate_batch.sh "$batch" "$out" "$MODEL" > "$OUT_DIR/$name.log" 2>&1; then
    echo "OK   $name"
  else
    echo "FAIL $name"
    return 1
  fi
}
export -f run_one
export OUT_DIR MODEL

ls "$BATCH_DIR"/batch_*.json | xargs -P "$PARALLEL" -I{} bash -c 'run_one "$@"' _ {}
echo "--- fin ---"
ls "$OUT_DIR"/batch_*.json 2>/dev/null | wc -l
