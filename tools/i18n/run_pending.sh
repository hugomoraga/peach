#!/usr/bin/env bash
# Traduce los lotes pendientes (tools/i18n/pending) en paralelo.
set -uo pipefail

PARALLEL="${1:-6}"
MODEL="${2:-opencode/big-pickle}"
# El repo se deduce de donde está este script: la ruta depende de dónde se
# clonó y no puede ir escrita en el archivo.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.opencode/bin:$PATH"

IN_DIR="tools/i18n/pending"
OUT_DIR="tools/i18n/pendout"
mkdir -p "$OUT_DIR"

run_one() {
  local batch="$1"
  local name out
  name="$(basename "$batch" .json)"
  out="$OUT_DIR/$name.json"
  if [ -s "$out" ]; then echo "SKIP $name"; return 0; fi
  if ./tools/i18n/translate_batch.sh "$batch" "$out" "$MODEL" > "$OUT_DIR/$name.log" 2>&1; then
    echo "OK   $name"
  else
    echo "FAIL $name"
    return 1
  fi
}
export -f run_one
export OUT_DIR MODEL

ls "$IN_DIR"/pend_*.json | xargs -P "$PARALLEL" -I{} bash -c 'run_one "$@"' _ {}
echo "--- fin ---"
ls "$OUT_DIR"/pend_*.json 2>/dev/null | wc -l
