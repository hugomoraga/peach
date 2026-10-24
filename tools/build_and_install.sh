#!/usr/bin/env bash
# Compila Videodrome en español y deja la app instalada lista para probar.
#
#   tools/build_and_install.sh              # compila, instala y arranca
#   tools/build_and_install.sh --build-only # sólo compila
#   tools/build_and_install.sh --no-launch  # compila e instala sin arrancar
#
# Qué hace, en orden:
#   1. compila el frontend en español sobre una copia aislada (tools/i18n);
#   2. empaqueta la app de escritorio con PyInstaller;
#   3. sustituye la app instalada en /Applications;
#   4. la arranca y dice dónde mirar.
#
# Los datos del usuario (~/Library/Application Support/Videodrome/peach-data) no
# se tocan: la app los busca aparte del bundle.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUILD_ONLY=0
LAUNCH=1
for argument in "$@"; do
  case "$argument" in
    --build-only) BUILD_ONLY=1 ;;
    --no-launch) LAUNCH=0 ;;
    *) echo "Opción desconocida: $argument" >&2; exit 2 ;;
  esac
done

APP_NAME="Videodrome"
BUILT="$ROOT/dist/macos.noindex/arm64/$APP_NAME.app"
INSTALLED="/Applications/$APP_NAME.app"
PORT="${VIDEODROME_PORT:-8911}"

# Node 24 lo pide el frontend: el build de Vite 8 no funciona con el 22.
if [ -d "$HOME/.nvm/versions/node/v24.22.1/bin" ]; then
  export PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH"
fi

echo "==> 1/4 compilando el frontend en español"
npm --prefix frontend run build

echo "==> 2/4 empaquetando la app"
.venv/bin/python -X utf8 scripts/build_macos_standalone.py --no-dmg --target-arch arm64

if [ "$BUILD_ONLY" = "1" ]; then
  echo "LISTO: $BUILT"
  exit 0
fi

echo "==> 3/4 instalando en $INSTALLED"
if [ -d "$INSTALLED" ]; then
  BACKUP="$HOME/Library/Application Support/Videodrome/previous-app.app"
  mkdir -p "$(dirname "$BACKUP")"
  rm -rf "$BACKUP"
  cp -R "$INSTALLED" "$BACKUP"
  echo "  la anterior quedó en $BACKUP"
fi
rm -rf "$INSTALLED"
cp -R "$BUILT" "$INSTALLED"
codesign --force --sign - "$INSTALLED" 2>/dev/null || true

if [ "$LAUNCH" = "0" ]; then
  echo "LISTO: app instalada en $INSTALLED"
  exit 0
fi

echo "==> 4/4 arrancando"
# La app instalada usa su propio directorio de datos; arrancarla con el
# entorno aquí hace que la prueba no toque la instalación real.
open -a "$INSTALLED"
echo
echo "LISTO: $APP_NAME está instalada y arrancada."
echo "  Interfaz: http://127.0.0.1:$PORT"
echo "  Datos:    ~/Library/Application Support/Videodrome/peach-data"
echo "  Para el smoke: node tools/i18n/verify_es.mjs http://127.0.0.1:$PORT"
