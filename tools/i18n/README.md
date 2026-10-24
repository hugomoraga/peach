# Peach en español

Fork de [peach-mitao/peach](https://github.com/peach-mitao/peach) con la
interfaz en español. El árbol de fuentes (`src/`, `frontend/src/`, `web/` y los
tests) se mantiene como en upstream, en chino. La traducción vive fuera y se
aplica en dos momentos:

- **Frontend:** durante la compilación, sobre una copia efímera en `.i18n/es/`.
  El único artefacto versionado que cambia es `web/dist/`.
- **Backend:** al servir la app, cuando `PEACH_LOCALE=es`. Un middleware
  traduce solo los campos de interfaz de las respuestas JSON y el título de
  las páginas del servidor. Está apagado por defecto para que los tests sigan
  viendo el texto de upstream.

`peach serve` activa el modo español por sí solo; `PEACH_LOCALE=zh` lo apaga.

## Por qué así

Editar el español dentro de `src/` y `frontend/src/` haría que cada actualización
de upstream chocara en cientos de archivos. Además, los tests comparan contra
texto chino: si el árbol se traduce en sitio, la suite falla y hay que adaptar
miles de aserciones. Mantener la fuente en chino deja los merges limpios y la
suite intacta; la calidad del español se verifica aparte, con comprobaciones
propias del build.

## Ficheros

```
tools/i18n/glossary.zh-es.json      glosario completo (zh -> es)
tools/i18n/seed-glossary.json       términos canónicos
tools/i18n/manual-glossary-*.json   lotes revisados a mano
tools/i18n/STYLE.es.md              guía de estilo
tools/i18n/translate.py             traduce Python y parte del frontend
tools/i18n/translate_frontend.mjs   segunda pasada con el AST de TypeScript
tools/i18n/build_frontend.py        copia, traduce, compila y publica web/dist
tools/i18n/coverage.py              cadenas de interfaz sin traducir
tools/i18n/validate.py              placeholders y sintaxis
tools/i18n/check_data.py            los valores de dato llegan intactos
tools/i18n/media-sources.es.json    etiquetas de fuentes que no son marca
tools/i18n/units.es.json            unidades de presentación por archivo
tools/i18n/verify_es.mjs            smoke de navegador sobre la app en español
```

### Valores que no se traducen

Algunas palabras son a la vez sufijo visible y valor que se guarda. El
glosario global no puede decidir, así que hay tres listas explícitas:

- `manual-glossary-10.json` (`exclude`): valores de dato que salen del
  glosario y no se traducen jamás (`速食`, `短`, `中`, `长`… son las bandas de
  duración que se escriben en la base).
- `units.es.json`: unidades de presentación de dos archivos concretos
  (`个` → `elementos`, `万` → `mil`).
- `media-sources.es.json`: etiquetas genéricas de las fuentes de medios; las
  marcas (`PikPak`, `115`) se quedan.

`check_data.py` compara byte a byte los archivos de etiquetas, géneros, kanji,
estudios y títulos JAV, las bandas de duración y calidad una a una, y el
registro de fuentes campo a campo. El build se detiene si algo cambia.


## Compilar

```bash
cd frontend && npm ci && cd ..
npm --prefix frontend run build       # build español -> web/dist/
npm --prefix frontend run build:raw   # build sin traducir, para comparar
```

El build español:

1. copia el repositorio versionado a `.i18n/es/` (ignorado por Git);
2. fija el locale `es-ES` (fechas, números, orden, documento y reproductor);
3. aplica el glosario y la pasada AST;
4. comprueba cobertura, placeholders y texto residual;
5. compila Vite en la copia y publica `web/dist/`.

No escribe en `src/`, `frontend/src/` ni `frontend/test/`. Después de compilar,
`git status` solo debe mostrar cambios en `web/dist/`.

## Tests

La suite se ejecuta sobre el árbol chino y no necesita glosario ni helpers de
traducción en las aserciones:

```bash
npm --prefix frontend test
./scripts/test.sh full
```

La capa española tiene sus propias comprobaciones:

- `tests/test_web_ui_translation.py`: el middleware solo toca campos de
  interfaz, los datos quedan intactos y el modo está apagado por defecto.
- `tests/test_frontend_build.py`: el bundle publicado trae las etiquetas en
  español y no conserva las chinas equivalentes.
- `tools/i18n/coverage.py --check`: una cadena nueva sin traducir no puede
  entrar sin actualizar la línea base.
- `tools/i18n/check_data.py`: los valores de dato llegan intactos al build.
- `tools/i18n/verify_es.mjs`: con la app en marcha, un navegador en chino
  ve la página de inicio de sesión en español, sin un solo carácter chino.


## Qué no se traduce

Son valores de datos, no interfaz:

- etiquetas de contenido y géneros (`毒龙`, `骑乘`, `蘿莉塔`…);
- títulos de producto, nombres de estudio y de persona;
- rutas, claves de configuración, valores de enum y campos JSON;
- cadenas que el código guarda o compara contra una fuente.

Traducirlas rompería el matching y dejaría registros huérfanos. El middleware
solo traduce `detail`, `error`, `help`, `hint`, `label`, `message`, `msg`,
`notice`, `reason`, `status_text` y `warning`; el resto se copia tal cual.

## Actualizar desde upstream

```bash
git fetch upstream
git rebase upstream/master
.venv/bin/python -X utf8 tools/i18n/extract_strings.py .
.venv/bin/python -X utf8 tools/i18n/coverage.py --check
# traducir solo lo nuevo (lotes manuales o run_all.sh)
.venv/bin/python -X utf8 tools/i18n/build_glossary.py --base tools/i18n/glossary.zh-es.json
npm --prefix frontend run build
npm --prefix frontend test
./scripts/test.sh full
```

Las entradas que no cambian conservan su traducción. Una cadena nueva o
modificada aparece como pendiente y el build de release no debe publicarse
hasta revisarla.

## Requisitos

- Python 3.14 y `uv`
- Node >= 24
- `pyinstaller` y `dmgbuild` solo para empaquetar
