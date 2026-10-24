#!/usr/bin/env bash
# Traduce un lote de cadenas con OpenCode.
# Uso: translate_batch.sh <batch.json> <salida.json> [modelo]
set -euo pipefail

BATCH="$1"
OUT="$2"
MODEL="${3:-opencode/big-pickle}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p "$(dirname "$OUT")"

PROMPT=$(cat <<'EOF'
Eres un traductor profesional zh→es para la interface de "Peach", una app
personal de medios (cine/AV) local-first, de un solo usuario.

Tarea: rellena el campo "es" de cada item del JSON de entrada con su
traducción al español.

RECURSOS (léelos antes de traducir):
- tools/i18n/STYLE.es.md  → guía de estilo, tabla de términos y reglas
- tools/i18n/seed-glossary.json → glosario canónico ya decidido

REGLAS:
1. Si una cadena aparece en seed-glossary.json, USA esa traducción exacta.
2. Si NO es UI (es un valor de base de datos: etiqueta de contenido, género,
   título de producto, nombre propio japonés/chino, URL, clave), deja "es" en
   "" y no la traduzcas. Esos NO se traducen.
3. Conserva los placeholders tal cual: ${n}, {count}, %s, {}, etc.
4. No inventes texto que no esté en el chino.
5. Conciso: la UI es densa.
6. Salida: el MISMO JSON con "es" rellenado. JSON puro, sin markdown, sin
   bloque de código, sin explicaciones.
EOF
)

opencode run --title "i18n $(basename "$BATCH" .json)" \
  --agent traductor --model "$MODEL" --format default "$PROMPT" \
  < "$BATCH" > "$OUT.raw" 2>"$OUT.err" || {
    echo "FALLO opencode: $(basename "$BATCH")" >&2
    exit 1
  }

python3 - "$OUT.raw" "$OUT" <<'PYEOF'
import json, re, sys

raw = open(sys.argv[1], encoding="utf-8").read().strip()
raw = re.sub(r"^```(?:json)?\s*", "", raw)
raw = re.sub(r"\s*```$", "", raw)
start = raw.find("{")
end = raw.rfind("}")
if start < 0 or end <= start:
    raise SystemExit("no se encontró objeto JSON en la salida")
data = json.loads(raw[start:end + 1])
if not isinstance(data, dict) or "items" not in data:
    raise SystemExit("la salida no tiene la forma {\"items\": [...]}")
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
filled = sum(1 for i in data["items"] if i.get("es"))
print(f"OK {filled}/{len(data['items'])} traducidas")
PYEOF
