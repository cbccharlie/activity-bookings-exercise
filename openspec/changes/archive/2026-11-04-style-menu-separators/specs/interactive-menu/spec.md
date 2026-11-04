# Spec Delta

## MODIFIED Requirements

### Requirement: Menú principal
El sistema SHALL mostrar un menú de selección con flechas y Enter, agrupado por secciones:
actividades (`List activities`, `Show an activity`, `Create an activity`, `Update an activity`,
`Delete an activity`, `Change an activity's status`), reservas (`Book an activity`, `My bookings`,
`Show a booking`), cuenta (`Register`, `Log in`, `Log out`, `Who am I`), `Show configuration` y
`Exit`. Los títulos de sección SHALL mostrarse atenuados, con un estilo distinto del de las
opciones, y no SHALL poder seleccionarse.

#### Scenario: Opciones del menú
- **WHEN** se abre el menú
- **THEN** la selección ofrece las opciones anteriores en ese orden, terminando en `Exit`

#### Scenario: Títulos de sección atenuados
- **WHEN** se abre el menú en un terminal
- **THEN** los títulos `── Activities ──`, `── Bookings ──`, `── Account ──` y `── Settings ──` se muestran con el estilo atenuado (gris del tema del terminal)
- **AND** las opciones se muestran sin ese estilo
- **AND** los títulos no se pueden seleccionar
