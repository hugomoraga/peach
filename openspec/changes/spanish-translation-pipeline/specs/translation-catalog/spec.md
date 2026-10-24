## Purpose

Define el catálogo revisable de mensajes zh→es que alimenta la app en español, con contexto, clasificación interfaz/dato, terminología y evidencia de revisión humana.

## ADDED Requirements

### Requirement: Entradas por texto fuente exacto

El catálogo SHALL asignar una traducción aprobada a cada unidad de mensaje por su texto chino exacto. Una entrada MUST cubrir el literal completo o la plantilla completa con sus interpolaciones; MUST NOT usarse para sustituir fragmentos sueltos de una frase.

#### Scenario: Mismo texto, dos contextos

- **WHEN** el texto `关闭` aparece como botón de un diálogo y como etiqueta de estado con significados distintos
- **THEN** cada aparición se trata como una unidad revisable y puede recibir una traducción distinta mediante una entrada específica de su literal

#### Scenario: Texto movido de archivo

- **WHEN** upstream mueve un literal sin cambiar su texto ni su contexto visible
- **THEN** la sincronización conserva la traducción aprobada y la reporta como reubicada, no como nueva

#### Scenario: Frase compuesta

- **WHEN** la interfaz compone una frase con varios literales
- **THEN** la traducción se aplica a la plantilla completa o a un parche de mensaje revisado, nunca a la suma de fragmentos

### Requirement: Clasificación interfaz o dato

Cada entrada SHALL declarar si es texto de interfaz (`ui`) o un valor de dato (`data`), con una razón cuando sea `data`. Las entradas `data` MUST NOT aplicarse al build.

#### Scenario: Etiqueta de contenido

- **WHEN** una cadena es una etiqueta de contenido, género, título de producto, nombre propio, ruta, clave de configuración o valor de enum
- **THEN** se clasifica como `data` y el build la deja byte a byte igual que upstream

#### Scenario: Texto de interfaz ambiguo

- **WHEN** una cadena parece interfaz pero también se guarda o se compara contra una fuente
- **THEN** queda como `data` hasta que una revisión demuestre que solo se muestra

### Requirement: Solo se aplican entradas aprobadas

El build de release SHALL aplicar únicamente entradas `ui` con estado `approved`. Una cadena `ui` sin entrada aprobada MUST impedir el build de release y aparecer en el informe con archivo y línea.

#### Scenario: Cadena sin traducir

- **WHEN** una cadena de interfaz de upstream no tiene entrada aprobada
- **THEN** el build de release falla y lista la cadena, el archivo y la línea

#### Scenario: Build de preview

- **WHEN** se solicita un build de preview con cadenas pendientes
- **THEN** el artefacto se marca como no distribuible y el informe enumera las cadenas que quedaron en chino

### Requirement: Mensajes completos, no fragmentos

El catálogo SHALL traducir mensajes completos. Una entrada MUST corresponder a un literal íntegro o a una unidad de mensaje declarada; las entradas que solo cubren un fragmento de una frase MUST NOT usarse para componer texto en tiempo de ejecución.

#### Scenario: Frase compuesta por partes

- **WHEN** la interfaz compone una frase uniendo varios literales chinos
- **THEN** la unidad de traducción es la frase completa o existe un parche de mensaje revisado, nunca la suma de fragmentos traducidos por separado

#### Scenario: Plantilla con interpolación

- **WHEN** el literal contiene interpolaciones
- **THEN** se traduce la plantilla completa y se conservan las interpolaciones en su posición y orden

### Requirement: Terminología y estilo consistentes

Las entradas aprobadas SHALL cumplir `tools/i18n/STYLE.es.md` y la tabla de términos canónicos. Un mismo concepto MUST usar el mismo término en todas las superficies, salvo que la revisión registre una excepción.

#### Scenario: Término canónico

- **WHEN** dos superficies traducen el mismo concepto chino
- **THEN** ambas usan el término canónico de la tabla

#### Scenario: Excepción justificada

- **WHEN** el contexto exige una palabra distinta
- **THEN** la entrada registra la excepción y el motivo, y la comprobación de términos la acepta

### Requirement: Evidencia de revisión por superficie

Cada superficie visible SHALL tener un registro de revisión con las entradas que la componen, la persona que revisó, la fecha y el resultado. Ninguna entrada `ui` MUST pasar a `approved` sin ese registro.

#### Scenario: Revisión de una página

- **WHEN** se revisa una página y se aprueban sus textos
- **THEN** el registro guarda la ruta, las entradas aprobadas, la fecha y el revisor

#### Scenario: Entrada sin revisión

- **WHEN** una entrada no aparece en ningún registro de revisión
- **THEN** permanece como candidata y no se aplica en un build de release

### Requirement: Catálogo versionado y auditable

El catálogo SHALL vivir en el repositorio como datos versionados. Cada cambio de traducción MUST ser revisable en un diff y atribuible a una entrada, sin depender de estado generado fuera del repositorio.

#### Scenario: Cambio de redacción

- **WHEN** se corrige la traducción de una entrada
- **THEN** el diff muestra la clave, el texto anterior, el texto nuevo y el estado de revisión
