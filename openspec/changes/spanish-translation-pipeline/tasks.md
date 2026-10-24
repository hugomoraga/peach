## 1. Recuperar una base limpia

- [x] 1.1 Etiquetar `feature/spanish-translation` como `archive/spanish-translation-v1` y crear la rama de trabajo desde `master`.
- [x] 1.2 Confirmar que la base parte de `master` y que los cambios del fork quedan aislados en los archivos de integración.
- [x] 1.3 Portar `tools/i18n/STYLE.es.md`, `seed-glossary.json` y los lotes manuales útiles; excluir el codemod de tests y los artefactos generados para tests.
- [x] 1.4 Inventariar las traducciones reutilizables: el glosario conserva 5.451 entradas y las que son valor de dato salen a `manual-glossary-10.json`.

## 2. Catálogo y extracción

- [x] 2.1 Definir el glosario como fuente única (`tools/i18n/glossary.zh-es.json`), con lotes manuales, exclusiones de dato y validación de placeholders.
- [x] 2.2 Extraer literales completos del frontend y del backend con su ubicación, y añadir una segunda pasada con el AST de TypeScript para las plantillas que el escáner no ve.
- [ ] 2.3 Reasociación por delta: sin cambios, nueva, modificada, reubicada y obsoleta, con tests de cada caso.
- [ ] 2.4 Comprobación de terminología canónica y excepciones declaradas, con tests.

## 3. Build español aislado

- [x] 3.1 Workspace aislado (`.i18n/es`) sin escribir en el árbol de fuentes; `git status` solo cambia `web/dist/`.
- [x] 3.2 Sustitución exacta de literales completos, más la pasada AST y el mapa de unidades por archivo.
- [x] 3.3 Mecanismo de parches acotados: `units.es.json` y `media-sources.es.json` declaran los casos que el glosario global no puede decidir; el build falla si el archivo declaration no existe.
- [x] 3.4 Locale `es-ES` en documento, fechas, números, orden, react-aria, reproductor y textos del backend.
- [ ] 3.5 Modos `preview` (no distribuible) y `release` (estricto) con su informe.
- [ ] 3.6 Modo de desarrollo traducido para revisar superficies sin empaquetar.

## 4. Traducción y revisión por superficie

- [x] 4.1 Navegación, shell, menús, estados vacíos y componentes comunes.
- [x] 4.2 Acceso, primera ejecución, instalación y errores de acceso.
- [x] 4.3 Inicio, catálogo, filtros, ordenación y búsqueda.
- [x] 4.4 Ficha de entidad, detalle de título, imágenes y reproductor.
- [x] 4.5 Seguimiento, fuentes, alias y feed.
- [x] 4.6 Ajustes, bibliotecas, diagnóstico y mantenimiento.
- [x] 4.7 Recolección, procesamiento, limpieza, revisión, estadísticas y gustos.
- [x] 4.8 Mensajes del backend, errores, CLI, bandeja y páginas servidas.
- [ ] 4.9 Capturas y registro de revisión por superficie (empezado: login y `/api/sources` con 0 caracteres chinos).

## 5. Verificación

- [x] 5.1 Ratchet de cobertura: una cadena nueva sin traducir no puede entrar sin actualizar la línea base (369 pendientes).
- [x] 5.2 Puerta de placeholders: falla si cambia, desaparece o se duplica un placeholder.
- [ ] 5.3 Puerta de texto mixto: fallar si una entrada mezcla chino y español sin declararlo.
- [x] 5.4 Integridad de datos: etiquetas, géneros, kanji, estudios, títulos JAV, bandas de duración y calidad y el registro de fuentes.
- [x] 5.5 Smoke de navegador: `tools/i18n/verify_es.mjs` comprueba título, `lang`, locale de react-aria y texto visible sin caracteres chinos.
- [x] 5.6 El build se detiene ante datos alterados, placeholders rotos o cobertura nueva.
- [ ] 5.7 Suite completa en verde. Los cuatro fallos que quedan son de `master`: se comprobó con un worktree en `de22796c` y fallan igual (`test_no_unregistered_directory_lingers` — la app crea `peach-data` junto al worktree; `test_known_python_file_execute_mode_requires_full`; `test_rendered_times_are_local_while_stored_times_stay_utc` — cambio de hora; `test_the_questions_cover_every_field_in_order_with_defaults_and_copy`). En `master` hay un quinto fallo, `test_the_bundle_is_committed_and_the_toolchain_is_not`, que esta rama sí resuelve: el bundle va en español.

## 6. Sincronización y documentación

- [ ] 6.1 Comando de sincronización con upstream e informe de delta; probar los cinco casos de reasociación.
- [x] 6.2 Runbook de actualización: fetch, rebase, reextracción, revisión, build, verificación y publicación.
- [x] 6.3 README del fork (`README.es.md`) y guía del pipeline (`tools/i18n/README.md`).

## 7. Cierre

- [x] 7.1 Verificar en macOS: la app sirve en español con `lang="es-ES"`, `PEACH_LOCALE=es` y el smoke sin chino.
- [ ] 7.2 Build de release sin pendientes ni datos alterados, con la suite verde.
- [ ] 7.3 Archivar la rama antigua y registrar la decisión final en `openspec/` y en la documentación del fork.
