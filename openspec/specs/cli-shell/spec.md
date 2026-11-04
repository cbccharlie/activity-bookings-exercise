# cli-shell Specification

## Purpose

Define el comando de consola `activity-bookings` como punto de entrada único del cliente: cómo se invoca, cómo informa de su ayuda y versión, y cómo comunica los errores al usuario mediante mensajes y códigos de salida.

## Requirements

### Requirement: Comando de consola instalable
El sistema SHALL exponer un comando de consola llamado `activity-bookings` disponible tras instalar el proyecto, ejecutable también como `python -m activity_bookings` con el mismo comportamiento.

#### Scenario: Ejecución mediante el comando instalado
- **GIVEN** el proyecto instalado en el entorno
- **WHEN** el usuario ejecuta `activity-bookings --help`
- **THEN** el proceso termina con código de salida 0
- **AND** la salida muestra el nombre del programa y la lista de subcomandos disponibles

#### Scenario: Ejecución como módulo
- **GIVEN** el proyecto instalado en el entorno
- **WHEN** el usuario ejecuta `python -m activity_bookings --help`
- **THEN** el proceso termina con código de salida 0 y muestra la misma ayuda que `activity-bookings --help`

### Requirement: Ayuda al invocar sin argumentos
Cuando el comando se invoca sin subcomando y la entrada o la salida estándar no son un terminal
interactivo, el sistema SHALL mostrar la ayuda sin ejecutar ninguna acción. Si ambas son un
terminal interactivo, SHALL abrir el menú interactivo (capacidad `interactive-menu`).

#### Scenario: Invocación sin argumentos
- **GIVEN** la entrada estándar no es un terminal interactivo
- **WHEN** el usuario ejecuta `activity-bookings` sin argumentos
- **THEN** la salida muestra la ayuda con la lista de subcomandos
- **AND** el proceso no realiza ninguna otra acción

#### Scenario: Invocación sin argumentos en un terminal
- **GIVEN** la entrada y la salida estándar son un terminal interactivo
- **WHEN** el usuario ejecuta `activity-bookings` sin argumentos
- **THEN** se abre el menú interactivo en lugar de la ayuda

#### Scenario: Un subcomando no abre el menú
- **GIVEN** la entrada y la salida estándar son un terminal interactivo
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** se ejecuta el subcomando `config` y no se abre el menú

### Requirement: Versión del cliente
El sistema SHALL mostrar la versión del paquete instalado con la opción `--version` y terminar con código 0.

#### Scenario: Consulta de versión
- **WHEN** el usuario ejecuta `activity-bookings --version`
- **THEN** la salida contiene `activity-bookings` seguido de la versión declarada del paquete
- **AND** el proceso termina con código de salida 0

### Requirement: Uso incorrecto de la CLI
El sistema SHALL rechazar subcomandos u opciones desconocidas con un mensaje de error de uso y código de salida 2.

#### Scenario: Subcomando desconocido
- **WHEN** el usuario ejecuta `activity-bookings foo`
- **THEN** la salida de error indica que el comando no existe
- **AND** el proceso termina con código de salida 2

#### Scenario: Opción desconocida
- **WHEN** el usuario ejecuta `activity-bookings --foo`
- **THEN** la salida de error indica que la opción no existe
- **AND** el proceso termina con código de salida 2

### Requirement: Errores de la aplicación legibles
El sistema SHALL presentar los errores de la aplicación como un mensaje breve en la salida de error, sin traza de Python, y terminar con código de salida 1.

#### Scenario: Error de aplicación controlado
- **GIVEN** un subcomando que falla por un error conocido de la aplicación (por ejemplo, configuración inválida)
- **WHEN** el usuario ejecuta ese subcomando
- **THEN** la salida de error muestra un mensaje que empieza por `Error:` y describe la causa
- **AND** la salida no contiene ninguna traza (`Traceback`)
- **AND** el proceso termina con código de salida 1
