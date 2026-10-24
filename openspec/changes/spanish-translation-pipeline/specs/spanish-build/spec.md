## Purpose

Produce los artefactos de Peach en español a partir del árbol de fuentes chino, de forma aislada, determinista y sin alterar el código ni los tests de upstream.

## ADDED Requirements

### Requirement: Build aislado del árbol de trabajo

El build español SHALL ejecutarse sobre una copia de trabajo propia y MUST NOT modificar `src/`, `frontend/src/`, `frontend/test/`, `tests/` ni ningún archivo de configuración. El único archivo versionado que puede cambiar es `web/dist/`, porque el proyecto publica ese artefacto.

#### Scenario: Build desde master limpio

- **WHEN** se ejecuta el build español sobre `master`
- **THEN** la app resultante está en español y `git status` solo muestra cambios en `web/dist/`

#### Scenario: Dos builds consecutivos

- **WHEN** se ejecuta el build dos veces con el mismo catálogo y el mismo commit
- **THEN** el segundo build no reutiliza ni sobrescribe archivos del primero y el resultado es equivalente

### Requirement: La suite de tests no depende del idioma

Los tests SHALL ejecutarse sobre el árbol de fuentes sin traducir. El build español MUST NOT requerir cambios en `frontend/test/**`, `frontend/e2e/**` ni `tests/**`, y las aserciones de texto chino MUST seguir siendo válidas.

#### Scenario: Tests después del build

- **WHEN** se ejecuta la suite completa después de compilar en español
- **THEN** la suite pasa sin haber modificado ni un archivo de tests

#### Scenario: Test que compara texto de interfaz

- **WHEN** un test compara contra un literal chino de upstream
- **THEN** lo hace contra el árbol chino y no necesita glosario, `tr()` ni resolución en tiempo de ejecución

### Requirement: Build determinista y sin red

El build SHALL producir el mismo resultado para las mismas entradas. MUST NOT depender de servicios de traducción, red ni estado local no versionado.

#### Scenario: Reproducibilidad

- **WHEN** dos máquinas compilan el mismo commit con el mismo catálogo y las mismas dependencias
- **THEN** obtienen artefactos equivalentes y el informe identifica la versión del catálogo usada

#### Scenario: Sin red

- **WHEN** el entorno no tiene salida a internet
- **THEN** el build español termina con las dependencias ya instaladas

### Requirement: Locale es-ES en toda la app

El artefacto SHALL presentar el idioma español de España: `lang="es-ES"` en el documento, formatos de fecha y número en `es-ES`, orden alfabético español, textos de react-aria en español y voz del reproductor en español.

#### Scenario: Documento servido

- **WHEN** se carga cualquier página del build español
- **THEN** el elemento raíz declara `lang="es-ES"`

#### Scenario: Formatos y orden

- **WHEN** la interfaz muestra una fecha, un número o una lista ordenada
- **THEN** usa las convenciones de `es-ES`

#### Scenario: Controles de react-aria

- **WHEN** se abre un selector, un calendario o un medidor
- **THEN** sus textos accesibles salen en español

### Requirement: Traducción del backend al servir

El backend SHALL traducir solo los campos de interfaz de sus respuestas cuando el modo español está activo, y MUST dejar intactos los campos de datos. El modo MUST estar apagado por defecto para que los tests y la CLI sigan viendo el texto de upstream; el proceso que sirve la app (`peach serve`) lo activa.

#### Scenario: Respuesta JSON

- **WHEN** el modo español está activo y una respuesta trae `error`, `message`, `label` o `help`
- **THEN** el valor visible se traduce y los campos de datos (títulos, etiquetas, géneros, rutas) se copian sin cambios

#### Scenario: Test fuera del modo español

- **WHEN** un test crea la app sin `PEACH_LOCALE=es`
- **THEN** recibe exactamente el texto de upstream

### Requirement: Un único origen de traducción

El build SHALL aplicar el catálogo aprobado, sin leer traducciones embebidas en el árbol de fuentes ni glosarios alternativos. El informe del build MUST declarar la versión del catálogo y el número de entradas aplicadas.

#### Scenario: Catálogo único

- **WHEN** el build aplica la traducción
- **THEN** solo usa el catálogo versionado y lo informa

#### Scenario: Catálogo inválido

- **WHEN** el catálogo no valida o falta una entrada requerida
- **THEN** el build falla antes de producir un artefacto distribuible

### Requirement: Artefactos de frontend, backend y empaquetado

El build SHALL cubrir el bundle web, la traducción del backend al servir y el empaquetado de escritorio. Los instaladores MUST generarse con el bundle traducido y el glosario incluido como dato de runtime.

#### Scenario: Instalador de escritorio

- **WHEN** se genera un instalador desde el build español
- **THEN** la app instalada abre en español, incluidos menú, bandeja y páginas del servidor

#### Scenario: Backend en el paquete

- **WHEN** se inicia la app empaquetada con `PEACH_LOCALE=es`
- **THEN** el middleware encuentra el glosario dentro del paquete y traduce sus respuestas

### Requirement: Modo de desarrollo traducido

El proyecto SHALL ofrecer una forma de levantar la app en español para revisión sin ejecutar el empaquetado completo.

#### Scenario: Revisión de una página

- **WHEN** se levanta el modo de desarrollo traducido
- **THEN** los cambios del catálogo se reflejan al recargar y la app sigue en español
