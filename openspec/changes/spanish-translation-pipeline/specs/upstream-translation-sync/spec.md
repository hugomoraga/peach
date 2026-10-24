## Purpose

Mantiene el fork al día con upstream sin volver a traducir toda la app ni arrastrar traducciones obsoletas, presentando solo el delta que necesita revisión.

## ADDED Requirements

### Requirement: Fuentes siempre de upstream

Tras sincronizar, el árbol de fuentes SHALL ser el de upstream, sin traducciones embebidas ni cambios de comportamiento. La traducción MUST vivir solo en el catálogo y en la capa de build.

#### Scenario: Rebase sobre upstream

- **WHEN** se actualiza el fork a un commit nuevo de upstream
- **THEN** `frontend/src/**`, `src/peach/**` y los tests coinciden con upstream y el build español sigue siendo posible

#### Scenario: Conflicto de traducción

- **WHEN** un conflicto afecta a un archivo de fuentes
- **THEN** se resuelve a favor de upstream y no se reintroduce texto español en el árbol

### Requirement: Reextracción por delta

La sincronización SHALL comparar el catálogo con las cadenas del commit nuevo y clasificar cada entrada como sin cambios, nueva, modificada, reubicada u obsoleta.

#### Scenario: Cadena nueva

- **WHEN** upstream añade un botón nuevo
- **THEN** aparece como pendiente y el build de release queda bloqueado hasta su aprobación

#### Scenario: Cadena modificada

- **WHEN** upstream cambia el texto chino de una entrada existente
- **THEN** la traducción anterior queda obsoleta y la entrada vuelve a revisión

#### Scenario: Cadena eliminada

- **WHEN** upstream elimina una cadena
- **THEN** su entrada se marca como obsoleta y deja de aplicarse sin borrar el historial

### Requirement: Conservar traducciones válidas

Las entradas sin cambios SHALL conservar su estado `approved` y su evidencia de revisión. Una reubicación solo MUST conservar la traducción cuando el texto y el contexto siguen siendo inequívocos.

#### Scenario: Archivo renombrado

- **WHEN** upstream renombra un archivo sin cambiar sus mensajes
- **THEN** las entradas se reasocian y siguen aprobadas

#### Scenario: Texto reutilizado en otro contexto

- **WHEN** el mismo texto chino aparece en una superficie nueva
- **THEN** no hereda automáticamente la aprobación de la superficie anterior y se revisa

### Requirement: Informe de sincronización

La sincronización SHALL producir un informe con el commit de origen, el commit de destino, los conteos por categoría y la lista de entradas que requieren revisión.

#### Scenario: Delta vacío

- **WHEN** no hay cadenas nuevas, modificadas ni reubicadas
- **THEN** el informe lo declara y el build puede continuar con las aprobaciones existentes

#### Scenario: Delta pendiente

- **WHEN** hay entradas nuevas o modificadas sin aprobar
- **THEN** el informe las enumera y el build de release no se permite

### Requirement: Verificación tras sincronizar

Tras cada sincronización SHALL ejecutarse la suite completa sobre el árbol chino y las comprobaciones del build español. Ambas MUST pasar antes de publicar el fork actualizado.

#### Scenario: Actualización publicable

- **WHEN** la suite china y las comprobaciones españolas pasan
- **THEN** la actualización se puede empaquetar y publicar

#### Scenario: Regresión en upstream

- **WHEN** la suite falla por un cambio de upstream ajeno a la traducción
- **THEN** la actualización se detiene y se reporta el fallo sin culpar al catálogo

### Requirement: Runbook reproducible

El repositorio SHALL documentar el procedimiento completo de actualización, desde el fetch hasta la publicación, con los comandos y los criterios de aceptación.

#### Scenario: Otra persona actualiza el fork

- **WHEN** alguien sigue el runbook desde un clon limpio
- **THEN** obtiene el mismo delta, las mismas comprobaciones y el mismo resultado
