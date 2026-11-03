# activity-browsing Specification

## Purpose

Permite explorar desde la CLI el catálogo público de actividades de la API ActivityBookings:
listarlas, buscarlas, ordenarlas y filtrarlas por estado, sin necesidad de iniciar sesión.

## Requirements

### Requirement: Subcomando de listado de actividades
El sistema SHALL ofrecer el subcomando `activity-bookings activities list`, dentro de un grupo
`activities` que aparece en la ayuda raíz, que consulta `GET <api_url>/activities` usando la URL de
la API de la configuración efectiva.

#### Scenario: Grupo activities en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings --help`
- **THEN** la lista de subcomandos incluye `activities`
- **AND** `activity-bookings activities --help` muestra el subcomando `list`

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"`
- **AND** la API responde 200 con `[]` a `GET http://api.example.com/activities`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** se realiza exactamente una petición `GET http://api.example.com/activities` sin parámetros de query
- **AND** el proceso termina con código de salida 0

#### Scenario: Configuración inválida
- **GIVEN** un fichero de configuración con `api_url = "ftp://example.com"`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error empieza por `Error:` e indica que `api_url` no es válida
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Listado público sin sesión
El sistema SHALL consultar el listado sin enviar credenciales, tanto si hay una sesión local como si
no la hay.

#### Scenario: Sin cabecera de autorización
- **GIVEN** la API responde 200 con una lista de actividades a `GET /activities`
- **WHEN** el usuario ejecuta `activity-bookings activities list` sin haber iniciado sesión
- **THEN** la petición no lleva cabecera `Authorization`
- **AND** el proceso termina con código de salida 0

### Requirement: Tabla de actividades
El sistema SHALL mostrar las actividades devueltas por la API, en el orden recibido, como una tabla
con las columnas ID, Name, Date, Location, Price, Capacity y Status, y una línea final con el número
de actividades mostradas.

#### Scenario: Listado con varias actividades
- **GIVEN** la API responde 200 con dos actividades: `activity-2` `City Bike Tour` (`date` `2026-12-20`, `location` `City Center`, `price` 35, `maxParticipants` 15, `status` `published`) y `activity-4` `Photography Walk` (`status` `draft`)
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida contiene las cabeceras `ID`, `Name`, `Date`, `Location`, `Price`, `Capacity` y `Status`
- **AND** la salida contiene `activity-2`, `City Bike Tour`, `2026-12-20`, `City Center`, `35.00`, `15` y `published`
- **AND** `City Bike Tour` aparece antes que `Photography Walk`
- **AND** la salida contiene `2 activities`
- **AND** el proceso termina con código de salida 0

#### Scenario: Se muestran todos los estados por defecto
- **GIVEN** la API responde 200 con actividades en estado `draft`, `published` y `cancelled`
- **WHEN** el usuario ejecuta `activity-bookings activities list` sin `--status`
- **THEN** la salida contiene las tres actividades

#### Scenario: Fecha con hora
- **GIVEN** la API responde 200 con una actividad cuya `date` es `2026-08-25T14:00:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida muestra la fecha como `2026-08-25 14:00 UTC`

#### Scenario: Fecha que no se puede interpretar
- **GIVEN** la API responde 200 con una actividad cuya `date` es `someday`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida muestra `someday` tal cual
- **AND** el proceso termina con código de salida 0

#### Scenario: Campos adicionales y updatedAt ausente
- **GIVEN** la API responde 200 con una actividad que incluye `slug`, `duration`, `userId` y `createdAt` pero no `updatedAt`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la actividad aparece en la tabla
- **AND** el proceso termina con código de salida 0

### Requirement: Listado vacío
El sistema SHALL indicar que no hay actividades cuando el resultado (tras búsqueda y filtros) está
vacío, sin mostrar la tabla, y terminar con código de salida 0.

#### Scenario: La API no devuelve actividades
- **GIVEN** la API responde 200 con `[]` a `GET /activities`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida contiene `No activities found.`
- **AND** la salida no contiene la cabecera `Location`
- **AND** el proceso termina con código de salida 0

### Requirement: Búsqueda por texto
El sistema SHALL aceptar `--search TEXT` y enviarlo a la API como parámetro de query `q`. Un texto
vacío o formado solo por espacios SHALL rechazarse como error de uso sin llamar a la API.

#### Scenario: Búsqueda enviada a la API
- **GIVEN** la API responde 200 con `[]` a `GET /activities?q=bike`
- **WHEN** el usuario ejecuta `activity-bookings activities list --search bike`
- **THEN** la petición lleva el parámetro de query `q` con valor `bike`
- **AND** el proceso termina con código de salida 0

#### Scenario: Búsqueda sin resultados
- **GIVEN** la API responde 200 con `[]` a `GET /activities?q=zzz`
- **WHEN** el usuario ejecuta `activity-bookings activities list --search zzz`
- **THEN** la salida contiene `No activities found.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Búsqueda vacía
- **WHEN** el usuario ejecuta `activity-bookings activities list --search " "`
- **THEN** la salida de error indica que `--search` no puede estar vacío
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Orden del listado
El sistema SHALL aceptar `--sort` con uno de `date`, `price`, `name` o `location`, y `--order` con
`asc` o `desc` (por defecto `asc`), y enviarlos a la API como `_sort` y `_order`. `--order` sin
`--sort` SHALL rechazarse como error de uso sin llamar a la API.

#### Scenario: Orden descendente por precio
- **GIVEN** la API responde 200 a `GET /activities?_sort=price&_order=desc` con dos actividades de precio 75 y 35, en ese orden
- **WHEN** el usuario ejecuta `activity-bookings activities list --sort price --order desc`
- **THEN** la petición lleva `_sort=price` y `_order=desc`
- **AND** en la salida la actividad de precio `75.00` aparece antes que la de `35.00`

#### Scenario: Orden ascendente por defecto
- **GIVEN** la API responde 200 con `[]`
- **WHEN** el usuario ejecuta `activity-bookings activities list --sort date`
- **THEN** la petición lleva `_sort=date` y `_order=asc`

#### Scenario: Búsqueda y orden combinados
- **GIVEN** la API responde 200 con `[]`
- **WHEN** el usuario ejecuta `activity-bookings activities list --search tour --sort name`
- **THEN** la petición lleva `q=tour`, `_sort=name` y `_order=asc`

#### Scenario: Campo de orden no válido
- **WHEN** el usuario ejecuta `activity-bookings activities list --sort capacity`
- **THEN** la salida de error indica que `capacity` no es un valor válido para `--sort`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Sentido de orden no válido
- **WHEN** el usuario ejecuta `activity-bookings activities list --sort date --order up`
- **THEN** la salida de error indica que `up` no es un valor válido para `--order`
- **AND** el proceso termina con código de salida 2

#### Scenario: --order sin --sort
- **WHEN** el usuario ejecuta `activity-bookings activities list --order desc`
- **THEN** la salida de error indica que `--order` requiere `--sort`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Filtro por estado
El sistema SHALL aceptar `--status` con uno de `draft`, `published`, `confirmed`, `sold-out`,
`done` o `cancelled` y mostrar solo las actividades con ese estado, filtrando en el cliente sin
enviar el estado a la API y conservando el orden recibido.

#### Scenario: Solo actividades publicadas
- **GIVEN** la API responde 200 con `Surf` (`draft`), `City Bike Tour` (`published`) y `Cooking Workshop` (`published`)
- **WHEN** el usuario ejecuta `activity-bookings activities list --status published`
- **THEN** la salida contiene `City Bike Tour` y `Cooking Workshop` y no contiene `Surf`
- **AND** la salida contiene `2 activities`
- **AND** la petición no lleva ningún parámetro `status`

#### Scenario: Ninguna actividad con ese estado
- **GIVEN** la API responde 200 con actividades que no están en estado `sold-out`
- **WHEN** el usuario ejecuta `activity-bookings activities list --status sold-out`
- **THEN** la salida contiene `No activities found.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Estado no válido
- **WHEN** el usuario ejecuta `activity-bookings activities list --status open`
- **THEN** la salida de error indica que `open` no es un valor válido para `--status`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Errores al consultar el listado
El sistema SHALL presentar los fallos de red, las respuestas de error de la API y las respuestas con
forma inesperada como un mensaje que empieza por `Error:` en la salida de error, sin traza de Python
y con código de salida 1.

#### Scenario: API caída
- **GIVEN** la conexión con la API es rechazada
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error contiene `Error: cannot connect to the API at http://localhost:3000`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Timeout
- **GIVEN** la API no responde a tiempo
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error contiene `Error:` e indica que la API no respondió a tiempo
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno de la API
- **GIVEN** la API responde 500 con `{"message": "Failed to retrieve activities", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error contiene `Error: API error 500: Failed to retrieve activities`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Ruta no encontrada en el servidor
- **GIVEN** la `api_url` apunta a un servidor que responde 404 con un cuerpo HTML a `GET /activities`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error contiene `Error: API returned HTTP 404 with an unexpected response`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta que no es una lista
- **GIVEN** la API responde 200 con `{"activities": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error empieza por `Error: invalid response from the API`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad incompleta
- **GIVEN** la API responde 200 con una lista que contiene una actividad sin `name`
- **WHEN** el usuario ejecuta `activity-bookings activities list`
- **THEN** la salida de error empieza por `Error: invalid response from the API` y menciona `name`
- **AND** el proceso termina con código de salida 1
