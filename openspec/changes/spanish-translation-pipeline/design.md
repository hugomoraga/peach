## Context

Ver `proposal.md` para la motivación. El estado actual deja 678 archivos traducidos en sitio, 272 tests frontend fallidos y un helper de tests que reconstruye español desde fragmentos. El árbol de `master` sigue en chino y su suite es la referencia que hay que conservar.

Restricciones que condicionan el diseño:

- Upstream publica varias veces por semana y escribe código, tests y documentación en chino.
- La interfaz se compone mucho con plantillas JS y HTML generado por concatenación; no hay capa de i18n.
- El objetivo es una app en español para uso personal, no un producto multiidioma con selector de idioma.
- Hay 6.812 literales únicos de aplicación (2.868 frontend, 4.088 Python) y 2.598 de ellos tienen cuatro caracteres o menos: muchos son datos, no interfaz.
- El intento anterior ya produjo 4.782 traducciones que corresponden a literales completos y se pueden reutilizar tras revisión.

## Goals / Non-Goals

**Goals:**

- Traducir sin tocar el árbol de fuentes ni los tests.
- Producir un build español reproducible desde un catálogo versionado y revisado.
- Detectar automáticamente cadenas sin traducir, placeholders rotos, texto mixto y datos alterados.
- Poder actualizar desde upstream traduciendo solo el delta.
- Dejar evidencia por superficie de que el español es correcto, no solo que existe.

**Non-Goals:**

- Selector de idioma en tiempo de ejecución o traducciones distintas de `es-ES`.
- Traducir etiquetas, géneros, títulos, nombres propios, rutas, claves o enums.
- Refactorizar toda la app a claves de mensaje (`t('key')`) ni reescribir la suite de upstream para que sea agnóstica al texto.
- Mantener la rama `feature/spanish-translation` como línea de desarrollo.

## Decisions

### 1. Traducción como capa de compilación, no como código fuente

El build parte de `git archive <commit>` en un directorio ignorado por Git (`build/es/`), aplica el catálogo sobre esa copia y compila allí. El repositorio nunca contiene español en `frontend/src` ni en `src/peach`.

**Por qué:** mantiene los merges de upstream limpios, deja la suite china intacta y permite reconstruir la app desde cualquier commit. Es el diseño que el README del fork ya declaraba, pero que el commit actual no cumplió.

**Alternativas descartadas:**

- **Traducir en sitio y adaptar tests** (estado actual): cada merge toca cientos de archivos y los tests dejan de verificar comportamiento.
- **Capa i18n completa con claves**: obliga a reescribir miles de literales y plantillas de upstream y a mantener un fork profundo; el coste supera el beneficio para un solo usuario.
- **Worktree de Git con la traducción commiteada**: sigue creando una rama traducida que hay que mergear; no resuelve el problema de fondo.

El build copia solo archivos versionados (`git archive`), enlaza o reutiliza `frontend/node_modules` y no escribe fuera de `build/es/`. Al terminar, `git status` debe seguir limpio.

### 2. Catálogo por contexto, no glosario global zh→es

Cada entrada se identifica por archivo, texto chino y ordinal de aparición; guarda el texto original, la traducción, la clasificación (`ui`/`data`), el estado (`candidate`/`approved`/`stale`/`obsolete`), el contexto visible y la evidencia de revisión. El mismo chino puede tener traducciones distintas en contextos distintos.

**Por qué:** un diccionario global aplana contextos, impide dos traducciones para el mismo texto y no distingue una etiqueta de un valor de base de datos. Es la causa directa de entradas como `De lejos a cerca` y de fragmentos traducidos por separado.

**Reutilización:** al reextraer, una entrada se reasocia por `(texto chino, contexto)`; si el archivo se movió y el texto es único, se traslada; si hay ambigüedad, vuelve a revisión. Las 4.782 entradas actuales que coinciden con literales completos entran como candidatas, no como aprobadas.

### 3. Unidad de traducción: mensaje completo o parche revisado

El extractor trabaja sobre literales completos: cadenas TS/JS/TSX, texto JSX, literales Python y plantillas con interpolaciones. Se traduce el literal entero; nunca se sustituyen trozos dentro de una frase.

**Por qué:** el español cambia el orden, el género y el número. Traducir fragmentos produce `端口正en使用`, `unidadeserror` y frases híbridas.

Para los casos en que la interfaz compone una frase con varias piezas, o necesita singular/plural, se admite un **parche de mensaje**: una transformación pequeña y revisada que se aplica a la copia de build (por ejemplo, sustituir una concatenación por una llamada a una función de mensaje con variantes `one`/`other`). Los parches:

- se guardan en `tools/i18n/patches/` con su justificación y la superficie afectada;
- se aplican con contexto y fallan ruidosamente si upstream ya no coincide;
- tienen un presupuesto reducido y una comprobación que impide que crezcan sin revisión.

**Alternativa descartada:** permitir composición de fragmentos con el glosario, que es lo que rompió la calidad del intento actual.

### 4. Datos y interfaz se clasifican explícitamente

La extracción propone una clasificación, pero la decisión se guarda en el catálogo. Son `data` las etiquetas de contenido, géneros, títulos, nombres de estudio y persona, rutas, claves de configuración, valores de enum y cualquier cadena que se guarde o se compare. Solo se traduce lo que se muestra y no participa en comparaciones.

**Por qué:** el build español debe conservar la lógica y el matching contra fuentes japonesas. Una etiqueta traducida rompe la biblioteca de forma silenciosa y los tests chinos no lo detectarían.

La comprobación de integridad compara los valores `data` del build con los del árbol de origen, y el smoke español recorre flujos que usan esos valores.

### 5. LLM para candidatos; revisión humana para aprobar

La traducción automática (lotes con contexto de archivo y pantalla) solo produce `candidate`. El estado `approved` exige revisión humana por superficie con capturas y registro.

**Por qué:** la calidad actual demuestra que una pasada automática sin revisión produce frases plausibles pero incorrectas, y que el error se propaga a los tests. La revisión por superficie permite detectar problemas de tono, longitud recortada y terminología.

La revisión se apoya en:

- `STYLE.es.md` y la tabla de términos canónicos;
- una comprobación de términos que detecta variantes prohibidas;
- capturas de los estados principales de cada página;
- un registro por superficie con commit, catálogo, revisor y fecha.

### 6. Los tests se quedan en chino; la traducción se verifica aparte

No se porta `translate_test_literals.py`, `frontend/test/react/text.ts` ni `glossary.zh-es.ts`. La suite de `master` se ejecuta sin cambios sobre el árbol chino y sigue siendo la red de seguridad de comportamiento.

**Por qué:** los tests actuales comparan texto de interfaz porque upstream así los escribió; cambiarlos para que sean agnósticos al idioma es un refactor grande y ajeno al objetivo. La traducción no debe ser motivo para debilitar la suite.

La capa española se verifica con pruebas propias del pipeline (esquema, extracción, sustituciones, parches) y con un smoke de navegador sobre el build español. Esas pruebas no viven en `frontend/test` ni dependen de `tr()`.

### 7. Sincronización por delta y catálogo histórico

`git fetch upstream` + rebase de la rama de tooling. El árbol se resuelve siempre a favor de upstream. Después se reextrae, se compara con el catálogo y se genera un informe de delta: sin cambios, nuevas, modificadas, reubicadas, obsoletas. Las entradas obsoletas se conservan con estado `obsolete` para no perder historial y no se aplican.

**Por qué:** traducir de nuevo 6.812 literales en cada actualización no es viable, y borrar entradas impide auditar por qué cambió una traducción.

### 8. Un solo informe de calidad bloquea el empaquetado

El pipeline produce un informe con cobertura, placeholders, texto mixto, integridad de datos, resultado del smoke y evidencia por superficie. Cualquier fallo detiene el empaquetado.

**Por qué:** el intento actual declaró éxito con la suite roja. El criterio de aceptación tiene que ser un artefacto verificable, no la impresión de que «casi todo» está traducido.

## Risks / Trade-offs

- **Volumen de revisión** (6.812 literales, 4.782 reutilizables) → priorizar por superficie, permitir builds de preview no distribuibles y revisar por lotes con capturas; no declarar release hasta cubrir las rutas principales.
- **El overlay no puede reordenar expresiones complejas** → presupuesto acotado de parches de mensaje, con fallo ruidoso si upstream cambia; el resto se traduce como mensaje completo.
- **La traducción de backend puede alterar lógica si se clasifica mal** → clasificación explícita, extracción a nivel de AST, comprobación de integridad de datos y smoke español de flujos reales.
- **Los parches y el catálogo envejecen con upstream** → reextracción por delta, estado `stale`, y puerta que bloquea el release con pendientes.
- **Coste de disco y tiempo del build aislado** → copiar solo archivos versionados, reutilizar `node_modules`, cachear dependencias y no duplicar medios ni datos.
- **La revisión humana sigue siendo el cuello de botella** → es deliberado: el objetivo es calidad, no velocidad. El pipeline hace visible lo que falta en vez de ocultarlo.
- **Riesgo de que alguien edite el árbol traducido** → `build/es/` ignorado por Git, reproducción desde cero en cada build y comprobación de `git status` limpio.

## Migration Plan

1. Etiquetar `feature/spanish-translation` como referencia (`archive/spanish-translation-v1`). No mergear.
2. Crear la rama de trabajo desde `master`.
3. Portar `STYLE.es.md`, `seed-glossary.json` y los lotes manuales; convertir a candidatas las traducciones que coincidan con literales completos y descartar las 617 entradas de fragmentos.
4. Implementar catálogo, extractor, validador y build aislado; borrar del proyecto los helpers y el codemod de tests.
5. Traducir y revisar por superficie, empezando por navegación, acceso, inicio, catálogo y ficha; seguir por el resto.
6. Añadir las comprobaciones de calidad y el smoke español.
7. Empaquetar y verificar en macOS; repetir en Windows si esa es la plataforma de uso.
8. Documentar el runbook de actualización y retirar la rama antigua tras la aceptación.

**Rollback:** la rama antigua y su tag se conservan; el build español se puede desactivar volviendo a `master`, que sigue siendo la app china funcional con su suite verde.

### Datos: dos mapas y una puerta

Palabras como `个` (unidades), `万` (diez mil) o `速食` (duración mínima) se usan
en dos sentidos: como sufijo visible y como valor que se guarda y se compara.
El glosario global no puede decidir, así que hay tres listas explícitas:

- `tools/i18n/manual-glossary-10.json` → `exclude`: valores de dato que salen
  del glosario y no se traducen jamás.
- `tools/i18n/units.es.json` → unidades de presentación de dos archivos
  concretos (`个` → `elementos`, `万` → `mil`).
- `tools/i18n/media-sources.es.json` → etiquetas genéricas de las fuentes de
  medios; las marcas (`PikPak`, `115`) se quedan.

`tools/i18n/check_data.py` compara los archivos de etiquetas, géneros, kanji,
estudios y títulos JAV byte a byte, las bandas de duración y calidad una a
una, y el registro de fuentes campo a campo. El build se detiene si algo de eso
cambia.

**Por qué:** con el glosario global, `速食` salía como `corto` en
`media_probe.py` y en `web_stats.py`: el build escribía una banda nueva en la
base y consultaba otra. La puerta lo detecta y frena el build.

## Implementación actual

El pipeline híbrido que quedó implementado en la rama `agent/opencode/spanish-build`:

- **Frontend:** `frontend/package.json` llama a `tools/i18n/build_frontend.py`. El script copia el árbol a `.i18n/es/`, fija el locale `es-ES`, aplica el glosario, aplica los mapas por archivo, ejecuta una segunda pasada con el AST de TypeScript (`translate_frontend.mjs`), comprueba cobertura, placeholders y datos, compila con Vite y publica `web/dist/`. Es el único artefacto versionado que cambia, y dos compilaciones seguidas dan el mismo `web/dist/`.
- **Backend:** `src/peach/ui_translation.py` traduce en runtime los campos de interfaz de las respuestas JSON y la cáscara HTML. Está apagado por defecto; `peach serve` activa `PEACH_LOCALE=es`. Los tests siguen viendo el texto de upstream. Los mensajes compuestos (`标签：原因`) se traducen solo si **las dos mitades** tienen traducción.
- **Catálogo:** el glosario (`tools/i18n/glossary.zh-es.json`, 5.451 entradas) es la fuente única. La pasada AST resolvió las plantillas que el escáner de Python no veía.
- **Datos:** `check_data.py` compara etiquetas, géneros, kanji, estudios, títulos JAV, bandas de duración y calidad y el registro de fuentes. La pasada AST excluye `core/tags.ts`, `core/jav-title.ts` y `react/boardui/**`.
- **Tests:** la suite de frontend vuelve a verde (1.651 tests) sin `tr()` ni glosario en las aserciones. `tests/test_web_ui_translation.py` cubre el middleware, la cáscara, el índice y los mensajes compuestos; `tests/test_frontend_build.py` comprueba el bundle español.
- **Smoke:** `tools/i18n/verify_es.mjs` abre `/login` con el navegador en chino y comprueba que el título, `lang`, el locale de react-aria y el texto visible salen en español, con 0 caracteres chinos.

### Límites conocidos de esta implementación

- La línea base de cobertura (369 formas) incluye comentarios, configuraciones y datos; el control es una ratchet contra cadenas nuevas, no una puerta de release con cobertura cero.
- No hay registro de revisión por superficie ni capturas para cada página; la aprobación sigue siendo la del glosario heredado más la revisión de los lotes nuevos.
- No hay modo `release` separado de `preview`; el build actual publica un artefacto no distribuible hasta completar la revisión.
- Quedan cadenas compuestas complejas (por ejemplo, el diálogo de fusión de alias) y textos de la bandeja/CLI sin traducir.
- La biblioteca BoardUI conserva datos de locale japonés/chino en el bundle; se excluyó de la traducción para no romper su lógica.


## Open Questions

- ¿La distribución objetivo es solo macOS en esta etapa o también Windows? Afecta el orden de verificación del empaquetado, no el diseño del catálogo ni del build.
- ¿Se quiere conservar un modo de preview no distribuible con texto chino pendiente para revisar por superficies, o se prefiere bloquear cualquier build hasta tener cobertura completa? El diseño ya contempla el modo preview; la decisión solo cambia el criterio de aceptación intermedio.
