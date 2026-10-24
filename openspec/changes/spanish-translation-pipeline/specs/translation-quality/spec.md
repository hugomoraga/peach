## Purpose

Verifica de forma independiente que el build español está completo, es coherente y no rompe datos, con evidencia reproducible por superficie antes de distribuir la app.

## ADDED Requirements

### Requirement: Cobertura de texto de interfaz

El informe de calidad SHALL enumerar todas las cadenas de interfaz del build y su estado. Un build de release MUST fallar si alguna cadena de interfaz queda en chino fuera de la lista explícita de datos.

#### Scenario: Botón sin traducir

- **WHEN** un botón visible conserva texto chino
- **THEN** la comprobación falla y reporta archivo, línea y texto

#### Scenario: Cadena de dato permitida

- **WHEN** el texto chino es una etiqueta, género, título o nombre propio clasificado como `data`
- **THEN** la comprobación lo acepta y no lo cuenta como pendiente

### Requirement: Placeholders intactos

Toda traducción SHALL conservar exactamente los placeholders de la cadena original, incluidos `${...}`, `{...}`, `%s`, `%d` y `{}`.

#### Scenario: Placeholder alterado

- **WHEN** una traducción cambia, elimina o duplica un placeholder
- **THEN** la entrada se rechaza y el build de release falla

#### Scenario: Placeholder reordenado

- **WHEN** el español necesita cambiar el orden de las palabras alrededor de un placeholder
- **THEN** el placeholder se conserva y solo cambia el texto que lo rodea

### Requirement: Sin texto mixto

Una entrada de interfaz MUST NOT mezclar caracteres chinos con texto español, salvo nombres propios o términos que la política de datos permita explícitamente.

#### Scenario: Cadena mixta

- **WHEN** una traducción contiene chino y español en la misma frase
- **THEN** la comprobación falla y la entrada vuelve a revisión

#### Scenario: Nombre propio dentro de una frase

- **WHEN** el chino incluye un nombre propio que debe mantenerse
- **THEN** la entrada declara ese fragmento como dato y la comprobación lo acepta

### Requirement: Valores de datos intactos

Los valores clasificados como `data` SHALL ser idénticos a upstream en el artefacto final. La comprobación MUST cubrir al menos etiquetas de contenido, géneros, títulos de producto, nombres de estudio y persona, rutas, claves de configuración y valores de enum.

#### Scenario: Etiqueta traducida por error

- **WHEN** una etiqueta de contenido aparece traducida en el build
- **THEN** la comprobación falla y señala la entrada y el valor original

#### Scenario: Valor de enum usado en lógica

- **WHEN** un valor que el código compara o guarda se altera en el build
- **THEN** la comprobación falla antes del empaquetado

### Requirement: Smoke de rutas principales

El build español SHALL pasar un smoke de navegador sobre las rutas principales: acceso e instalación, inicio, catálogo, ficha de entidad, detalle de título, seguimiento, ajustes, diagnóstico y reproductor.

#### Scenario: Ruta principal en español

- **WHEN** se abre una de las rutas principales del build español
- **THEN** la página carga sin errores de consola y muestra texto en español

#### Scenario: Flujo crítico

- **WHEN** se recorre un flujo crítico de cada superficie
- **THEN** la interacción termina con el resultado esperado y sin texto chino no permitido

### Requirement: Evidencia visual por superficie

Cada superficie revisada SHALL dejar capturas de pantalla y un registro con la ruta, el estado y la fecha. La evidencia MUST ser reproducible desde el mismo commit y catálogo.

#### Scenario: Revisión de una página

- **WHEN** se aprueba una superficie
- **THEN** quedan capturas de sus estados principales y el registro identifica commit y catálogo

#### Scenario: Superficie sin evidencia

- **WHEN** una superficie no tiene capturas ni registro
- **THEN** no se considera aprobada para distribución

### Requirement: Informe único de calidad

El proyecto SHALL producir un informe de calidad con el resultado de cada comprobación, los conteos y los ejemplos que fallan. El empaquetado MUST rechazar un informe con cualquier comprobación fallida.

#### Scenario: Todo en verde

- **WHEN** todas las comprobaciones pasan y la revisión está firmada
- **THEN** el build se marca como candidato a distribución

#### Scenario: Una comprobación falla

- **WHEN** cualquier comprobación falla
- **THEN** el empaquetado se detiene y el informe explica qué falló y dónde
