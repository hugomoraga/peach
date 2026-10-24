# Peach en español

Este fork mantiene la aplicación en español sin traducir el árbol de fuentes
de upstream. El código, los tests y la documentación de `peach-mitao/peach`
siguen en chino; la traducción se aplica al compilar el frontend y al servir
el backend.

- `upstream` es el repositorio original.
- `origin` es este fork.
- La guía completa del pipeline está en [`tools/i18n/README.md`](tools/i18n/README.md).

## Compilar y probar

```bash
cd frontend && npm ci && cd ..
npm --prefix frontend run build       # interfaz en español -> web/dist/
npm --prefix frontend test            # suite sobre el árbol chino
./scripts/test.sh full                # suite completa del proyecto
```

`peach serve` activa el modo español por sí solo. `PEACH_LOCALE=zh` lo apaga.

## Actualizar desde upstream

```bash
git fetch upstream
git rebase upstream/master
.venv/bin/python -X utf8 tools/i18n/extract_strings.py .
.venv/bin/python -X utf8 tools/i18n/coverage.py --check
.venv/bin/python -X utf8 tools/i18n/build_glossary.py --base tools/i18n/glossary.zh-es.json
npm --prefix frontend run build
./scripts/test.sh full
```

Las traducciones existentes se conservan; las cadenas nuevas aparecen como
pendientes y se revisan antes de publicar el artefacto.
