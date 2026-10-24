<p align="center">
  <img src="resources/videodrome-logo.png" alt="Videodrome" width="96">
</p>

<h1 align="center">Videodrome</h1>

<p align="center">Biblioteca personal de cine en español: disco local, unidades en la nube y las creadores que sigues, todo en un sitio.</p>

---

## Qué es esto

**Videodrome** es un fork personal de [Peach](https://github.com/peach-mitao/peach), la
aplicación original de [peach-mitao](https://github.com/peach-mitao). Todo el trabajo de
la app (el ledger, el scraping, el reproductor, la biblioteca, la bandeja del sistema)
es de Peach. Lo que este fork cambia es la lengua: **la interfaz está en español** y el
código se llama `videodrome`.

Peach es software libre bajo la **AGPL-3.0-or-later**. Este fork también lo es.

### Créditos y licencia

- **Peach**, por [peach-mitao](https://github.com/peach-mitao) y quienes contribuyen
  con él. Copyright (C) sus autores. Licencia [AGPL-3.0-or-later](LICENSE).
- **Videodrome**, este fork. Cambia el nombre, la lengua de la interfaz y el empaquetado;
  el motor es el de Peach.
- La traducción al español y el pipeline que la aplica son obra de este fork
  (`tools/i18n/`).

El código fuente de ambos es público: [peach-mitao/peach](https://github.com/peach-mitao/peach)
y [hugomoraga/peach](https://github.com/hugomoraga/peach).

AGPL-3.0 obliga a que quien recibe el programa pueda obtener su código fuente y a
que la interfaz muestre un aviso legal. Por eso el `.app` lleva la licencia dentro y
este README enuncia el origen.

## Cómo se usa

Es una aplicación de escritorio para macOS (también hay build de Windows). La bandeja
del sistema es el centro: desde ahí se abre la interfaz en el navegador, se configuran
las unidades y se lanzan las tareas.

```bash
# compilar la interfaz en español, empaquetar e instalar
tools/build_and_install.sh

# sólo compilar
tools/build_and_install.sh --build-only
```

Al terminar la app queda instalada en `/Applications/Videodrome.app` y los datos en
`~/Library/Application Support/Videodrome/peach-data`.

## Cómo está hecho

La diferencia de fondo con Peach es que **aquí no se traduce el código**.

- El árbol de fuentes (`src/`, `frontend/src/`, `web/`) sigue en chino, tal y como
  viene de upstream.
- La traducción vive en `tools/i18n/glossary.zh-es.json`: 5.400 mensajes con su
  traducción al español. `npm --prefix frontend run build` la aplica sobre una copia
  aislada (`.i18n/es/`) y publica el resultado en `web/dist/`.
- El backend traduce al servir, con `PEACH_LOCALE=es`, y sólo sobre los campos de
  interfaz: las etiquetas de contenido, los géneros y los títulos no se tocan.

Así, traer los cambios de upstream es un `git fetch upstream && git rebase upstream/master`
sin conflictos: lo único que hay que revisar son las cadenas nuevas.

### Puertas de calidad

El build se niega a continuar si algo va mal:

| Puerta | Qué vigila |
| --- | --- |
| `tools/i18n/coverage.py` | Una cadena de interfaz nueva sin traducir no entra sin revisión |
| `tools/i18n/validate.py` | Los placeholders (`${n}`, `{count}`) no se rompen |
| `tools/i18n/check_data.py` | Los valores guardados (etiquetas, géneros, bandas de duración) llegan intactos |
| `tools/i18n/verify_es.mjs` | En un navegador real, la página sale en español y sin un solo carácter chino |
| `frontend/test/**` | 1.651 tests de comportamiento, sin depender del idioma |

## Requisitos

- macOS con Python 3.14 或更高（`uv`）、Node 24 y las dependencias de `uv sync --locked --all-extras`
- Windows: `scripts/build_windows.ps1`

## Estructura

```
src/videodrome/      el motor (código de Peach, renombrado)
frontend/src/        la interfaz (código de Peach, en chino)
web/                 las páginas estáticas y el bundle publicado
tools/i18n/          el catálogo de traducción y el pipeline
docs/                documentación de upstream
openspec/            los planes de trabajo de este fork
```

## Documentación

- [`tools/i18n/README.md`](tools/i18n/README.md) — el pipeline de traducción, cómo
  actualizar el glosario y qué no se traduce.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — operar la app.
- [`docs/TESTING.md`](docs/TESTING.md) — cómo se prueba.
