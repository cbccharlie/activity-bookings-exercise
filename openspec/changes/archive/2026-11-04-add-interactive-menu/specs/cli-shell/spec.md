# Spec Delta

## MODIFIED Requirements

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
