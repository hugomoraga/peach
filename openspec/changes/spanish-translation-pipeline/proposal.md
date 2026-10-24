## Why

La rama `feature/spanish-translation` tradujo el árbol de fuentes en sitio (678 archivos) y, para que los tests siguieran pasando, sustituyó sus aserciones por un glosario resuelto en tiempo de ejecución (`tr()`, `sel()`, `attr()`). El resultado no es sostenible:

- La suite frontend tiene **272 tests fallidos de 1661** (medido con `npx vitest run`). La suite Python no se modificó: el intento de ejecutarla se detuvo porque el venv del checkout principal está desincronizado (64 paquetes), así que su estado real queda sin medir; sí hay **267 archivos de test con 2.540 líneas de aserción en chino** que comparan contra textos que el commit tradujo.
- El helper de tests reconstruye el español a partir de fragmentos chinos. Un cambio de redacción o una traducción distinta en la app rompe decenas de tests que no verifican comportamiento, sino cómo se compuso una frase.
- El glosario tiene **5.399 entradas**, pero **617 no son literales del código** (fragmentos y plantillas compuestas). Traducir fragmentos produce español agramatical: `De lejos a cerca`, `unidadeserror`, `añadir 3 elementos`, `ValueError: ValueError`.
- Quedan cadenas mixtas en producción, por ejemplo `将处理选中的 ${ids.length} 项。`, `将合并以下 ${items.length} 组创作者：` o `照片 · ${...}`.
- El diseño declarado del pipeline (traducir una copia, mantener el árbol en chino) no coincide con lo que se commiteó: el árbol ya está traducido y `build_es.sh` restaura esa misma copia traducida. Cada merge con upstream mueve 678 archivos en conflicto.

El objetivo sigue siendo una app en español. El problema es el método: se está manteniendo una traducción frágil dentro del código y se adaptó la suite al idioma en vez de mantenerla independiente.

## What Changes

- **BREAKING** Abandonar la traducción en sitio y el codemod de tests. La nueva rama parte de `master`; la rama actual se conserva como referencia, no se mergea.
- La traducción pasa a ser una **capa de compilación y de servicio**: el frontend se compila desde un workspace aislado; el backend traduce solo los campos de interfaz al servir la app. El árbol de fuentes y los tests siguen siendo los de upstream (chino) y no se modifican; el único artefacto versionado que cambia es `web/dist/`.
- Introducir un **catálogo de mensajes** con contexto, estado de revisión y política explícita de qué es texto de interfaz y qué es dato que nunca se traduce.
- Traducir **mensajes completos**, no fragmentos sueltos. Las pocas composiciones que el español necesita reordenar se resuelven con parches de mensaje revisados y acotados.
- Sustituir el glosario de tests por **puertas de calidad sobre el build español**: cobertura, placeholders, valores no traducidos, texto mixto y smoke visual por superficie.
- Reutilizar del intento actual lo que sí sirve: `STYLE.es.md`, el glosario semilla, los lotes manuales y las traducciones que correspondan a literales completos (4.782 entradas).
- Dejar un runbook de actualización con upstream: rebase, reextracción, traducir solo el delta, revisar, compilar y verificar.

## Capabilities

### New Capabilities

- `translation-catalog`: catálogo zh→es revisable, con clave estable, contexto, clasificación interfaz/dato, estado de aprobación y reglas de terminología.
- `spanish-build`: compilación determinista de la app en español desde el árbol chino sin modificar el working tree, con locale `es-ES` y workspace aislado.
- `translation-quality`: verificación del build español por cobertura, placeholders, texto mixto, valores de datos intactos y smoke visual de las rutas principales.
- `upstream-translation-sync`: actualización desde upstream que conserva traducciones existentes y presenta solo el delta nuevo o modificado para revisión.

### Modified Capabilities

<!-- No hay specs existentes en openspec/specs/; la suite de tests no cambia de contrato. -->

## Impact

- `tools/i18n/**`: se reescribe el pipeline; se eliminan `translate_test_literals.py`, `gen_glossary_module.py` y los artefactos de tests.
- `frontend/test/react/text.ts`, `frontend/test/react/glossary.zh-es.ts`: se eliminan. Los tests vuelven al contenido de `master` sin envoltorios `tr()`, `sel()` ni `attr()`.
- `scripts/build_es.sh`, `tools/i18n/set_locale_es.py`, `tools/i18n/apply_backend_i18n.py`: pasan a operar sobre una copia, no sobre el árbol de trabajo.
- `frontend/src/**` y `src/peach/**`: vuelven al chino de `master`; la traducción vive fuera.
- `web/dist/**` y el empaquetado macOS/Windows: se generan desde el workspace traducido.
- Documentación: README del fork y runbook de actualización; la guía de estilo se conserva.
- Sin cambios en ledger, esquema de datos, API ni valores de etiquetas/géneros.
