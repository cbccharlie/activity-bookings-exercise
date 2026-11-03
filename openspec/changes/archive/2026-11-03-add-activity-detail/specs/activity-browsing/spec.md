# Spec Delta

## ADDED Requirements

### Requirement: Subcomando de detalle de actividad
El sistema SHALL ofrecer el subcomando `activity-bookings activities show ACTIVITY_ID`, dentro del
grupo `activities`, que consulta `GET <api_url>/activities/<ACTIVITY_ID>` usando la URL de la API de
la configuración efectiva y codificando el ID como un único segmento de ruta.

#### Scenario: Subcomando show en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings activities --help`
- **THEN** la salida incluye el subcomando `show`

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"`
- **AND** la API responde 200 con la actividad `activity-2` a `GET http://api.example.com/activities/activity-2`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** se realiza exactamente una petición `GET http://api.example.com/activities/activity-2`
- **AND** el proceso termina con código de salida 0

#### Scenario: ID con caracteres reservados
- **GIVEN** la API responde 404 con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities show "a/b c"`
- **THEN** la petición se envía a la ruta `/activities/a%2Fb%20c`
- **AND** el proceso termina con código de salida 1

#### Scenario: Sin ID
- **WHEN** el usuario ejecuta `activity-bookings activities show`
- **THEN** la salida de error indica que falta el argumento `ACTIVITY_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: ID vacío
- **WHEN** el usuario ejecuta `activity-bookings activities show " "`
- **THEN** la salida de error indica que `ACTIVITY_ID` no puede estar vacío
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Configuración inválida en el detalle
- **GIVEN** un fichero de configuración con `api_url = "ftp://example.com"`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error empieza por `Error:` e indica que `api_url` no es válida
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Detalle público sin sesión
El sistema SHALL consultar el detalle de una actividad sin enviar credenciales, tanto si hay una
sesión local como si no la hay.

#### Scenario: Detalle sin cabecera de autorización
- **GIVEN** la API responde 200 con la actividad `activity-2` a `GET /activities/activity-2`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2` sin haber iniciado sesión
- **THEN** la petición no lleva cabecera `Authorization`
- **AND** el proceso termina con código de salida 0

### Requirement: Ficha de la actividad
El sistema SHALL mostrar la actividad como una ficha de pares campo-valor con las filas ID, Name,
Slug, Date, Duration, Location, Price, Min participants, Capacity, Status, Organizer y Created, y la
fila Updated solo si la API devuelve `updatedAt`. Las fechas se muestran con el mismo formato que en
el listado, la duración en minutos y el precio con dos decimales.

#### Scenario: Actividad completa
- **GIVEN** la API responde 200 con `activity-2` `City Bike Tour` (`slug` `city-bike-tour`, `date` `2026-12-20`, `duration` 120, `location` `City Center`, `price` 35, `minParticipants` 3, `maxParticipants` 15, `status` `published`, `userId` `user-1`, `createdAt` `2026-01-16T10:00:00.000Z`) sin `updatedAt`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida contiene las etiquetas `ID`, `Name`, `Slug`, `Date`, `Duration`, `Location`, `Price`, `Min participants`, `Capacity`, `Status`, `Organizer` y `Created`
- **AND** la salida contiene `activity-2`, `City Bike Tour`, `city-bike-tour`, `2026-12-20`, `120 min`, `City Center`, `35.00`, `3`, `15`, `published`, `user-1` y `2026-01-16 10:00 UTC`
- **AND** la salida no contiene la etiqueta `Updated`
- **AND** el proceso termina con código de salida 0

#### Scenario: Actividad modificada
- **GIVEN** la API responde 200 con una actividad que incluye `updatedAt` `2026-02-01T08:30:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida contiene la etiqueta `Updated` y el valor `2026-02-01 08:30 UTC`

#### Scenario: Fecha con hora en el detalle
- **GIVEN** la API responde 200 con una actividad cuya `date` es `2026-08-25T14:00:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-3`
- **THEN** la salida muestra la fecha como `2026-08-25 14:00 UTC`

#### Scenario: Fecha que no se puede interpretar en el detalle
- **GIVEN** la API responde 200 con una actividad cuya `createdAt` es `someday`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida muestra `someday` tal cual
- **AND** el proceso termina con código de salida 0

#### Scenario: Campos desconocidos
- **GIVEN** la API responde 200 con una actividad completa que además incluye un campo `extra`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la ficha se muestra sin el campo `extra`
- **AND** el proceso termina con código de salida 0

### Requirement: Errores al consultar el detalle
El sistema SHALL presentar la actividad inexistente, los fallos de red, las respuestas de error de
la API y las respuestas con forma inesperada como un mensaje que empieza por `Error:` en la salida de
error, sin traza de Python y con código de salida 1.

#### Scenario: Actividad inexistente
- **GIVEN** la API responde 404 con `{"message": "Activity not found", "errors": []}` a `GET /activities/activity-99`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-99`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: API caída en el detalle
- **GIVEN** la conexión con la API es rechazada
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error contiene `Error: cannot connect to the API at http://localhost:3000`
- **AND** el proceso termina con código de salida 1

#### Scenario: Timeout en el detalle
- **GIVEN** la API no responde a tiempo
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error contiene `Error:` e indica que la API no respondió a tiempo
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno al consultar el detalle
- **GIVEN** la API responde 500 con `{"message": "Failed to retrieve activity", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error contiene `Error: API error 500: Failed to retrieve activity`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: 404 sin formato de la API
- **GIVEN** la `api_url` apunta a un servidor que responde 404 con un cuerpo HTML a `GET /activities/activity-2`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error contiene `Error: API returned HTTP 404 with an unexpected response`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta que no es un objeto
- **GIVEN** la API responde 200 con `[]` a `GET /activities/activity-2`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error empieza por `Error: invalid response from the API`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad sin campo del detalle
- **GIVEN** la API responde 200 con una actividad sin `duration`
- **WHEN** el usuario ejecuta `activity-bookings activities show activity-2`
- **THEN** la salida de error empieza por `Error: invalid response from the API` y menciona `duration`
- **AND** el proceso termina con código de salida 1
