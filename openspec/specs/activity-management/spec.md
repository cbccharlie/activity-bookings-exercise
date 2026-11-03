# activity-management Specification

## Purpose

Permite que un usuario con sesión gestione desde la CLI sus propias actividades en la API
ActivityBookings: crearlas, modificarlas y borrarlas.

## Requirements

### Requirement: Subcomandos de gestión de actividades
El sistema SHALL ofrecer los subcomandos `create`, `update` y `delete` dentro del grupo
`activities`, junto al `list` existente.

#### Scenario: Subcomandos en la ayuda del grupo
- **WHEN** el usuario ejecuta `activity-bookings activities --help`
- **THEN** la salida contiene `list`, `create`, `update` y `delete`
- **AND** el proceso termina con código de salida 0

### Requirement: Alta de una actividad
El sistema SHALL crear una actividad con `activities create`, enviando `POST <api_url>/activities`
con el token de la sesión y un cuerpo JSON con `name`, `price`, `date`, `location`,
`minParticipants` y `maxParticipants` como números o cadenas según su tipo, más `duration` solo si
se indica. No SHALL enviar `status`.

#### Scenario: Cuerpo y cabecera enviados al crear
- **GIVEN** una sesión válida para `http://localhost:3000` con `access_token` `tok-123`
- **AND** la API responde 201 a `POST /activities` con una actividad `activity-5`
- **WHEN** el usuario ejecuta `activity-bookings activities create --name "Yoga" --price 20 --date 2027-01-15 --location "Park" --min-participants 2 --max-participants 10`
- **THEN** se realiza exactamente una petición `POST http://localhost:3000/activities` con la cabecera `Authorization: Bearer tok-123`
- **AND** el cuerpo JSON es `{"name": "Yoga", "price": 20, "date": "2027-01-15", "location": "Park", "minParticipants": 2, "maxParticipants": 10}`
- **AND** el proceso termina con código de salida 0

#### Scenario: Duración indicada
- **GIVEN** una sesión válida y la API responde 201 a `POST /activities`
- **WHEN** el usuario ejecuta `activities create` con todas las opciones obligatorias y `--duration 90`
- **THEN** el cuerpo JSON enviado contiene `"duration": 90`

#### Scenario: Precio con decimales
- **GIVEN** una sesión válida y la API responde 201 a `POST /activities`
- **WHEN** el usuario ejecuta `activities create` con `--price 12.5` y el resto de opciones obligatorias
- **THEN** el cuerpo JSON enviado contiene `"price": 12.5`

### Requirement: Resultado de un alta correcta
Tras un alta correcta, el sistema SHALL indicar que la actividad se ha creado con su ID y mostrar
sus datos (ID, Name, Date, Location, Price, Capacity y Status) tal como los devuelve la API.

#### Scenario: Actividad creada
- **GIVEN** la API responde 201 con `{"id": "activity-5", "name": "Yoga", "slug": "yoga", "price": 20, "date": "2027-01-15", "duration": 60, "location": "Park", "minParticipants": 2, "maxParticipants": 10, "status": "draft", "userId": "user-1", "createdAt": "2026-11-03T10:00:00.000Z"}`
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida contiene `Activity activity-5 created.`
- **AND** la salida contiene `Yoga`, `2027-01-15`, `Park`, `20.00`, `10` y `draft`
- **AND** la salida no contiene `tok-123`

### Requirement: Opciones obligatorias del alta
El sistema SHALL rechazar como error de uso, con código 2 y sin llamar a la API, un alta a la que le
falte una opción obligatoria o con un valor numérico que no se pueda interpretar.

#### Scenario: Falta una opción obligatoria
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activities create` sin `--location`
- **THEN** la salida de error menciona `--location`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Número no válido
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activities create` con `--max-participants diez` y el resto de opciones obligatorias
- **THEN** la salida de error menciona `--max-participants`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Modificación de una actividad
El sistema SHALL modificar una actividad con `activities update ACTIVITY_ID`, enviando
`PUT <api_url>/activities/<ACTIVITY_ID>` con el token de la sesión y un cuerpo JSON que contiene solo
los campos indicados, con los números como números JSON. No SHALL enviar `status`.

#### Scenario: Solo se envían los campos indicados
- **GIVEN** una sesión válida con `access_token` `tok-123`
- **AND** la API responde 200 a `PUT /activities/activity-5`
- **WHEN** el usuario ejecuta `activity-bookings activities update activity-5 --price 25 --max-participants 12`
- **THEN** se realiza exactamente una petición `PUT http://localhost:3000/activities/activity-5` con la cabecera `Authorization: Bearer tok-123`
- **AND** el cuerpo JSON es `{"price": 25, "maxParticipants": 12}`

#### Scenario: Actividad actualizada
- **GIVEN** la API responde 200 a `PUT /activities/activity-5` con la actividad con `name` `Yoga al aire libre` y `price` 25
- **WHEN** el usuario ejecuta `activities update activity-5 --name "Yoga al aire libre" --price 25`
- **THEN** la salida contiene `Activity activity-5 updated.`
- **AND** la salida contiene `Yoga al aire libre` y `25.00`
- **AND** el proceso termina con código de salida 0

### Requirement: Modificación sin cambios
El sistema SHALL rechazar como error de uso, con código 2 y sin llamar a la API, un `update` sin
ningún campo que modificar o sin `ACTIVITY_ID`.

#### Scenario: Ningún campo indicado
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities update activity-5`
- **THEN** la salida de error indica que hay que indicar al menos un campo
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Falta el ID
- **WHEN** el usuario ejecuta `activity-bookings activities update --price 25`
- **THEN** la salida de error menciona `ACTIVITY_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Borrado de una actividad
El sistema SHALL borrar una actividad con `activities delete ACTIVITY_ID`, enviando
`DELETE <api_url>/activities/<ACTIVITY_ID>` con el token de la sesión tras la confirmación del
usuario, e indicar que se ha borrado.

#### Scenario: Borrado confirmado
- **GIVEN** una sesión válida con `access_token` `tok-123`
- **AND** la API responde 204 sin cuerpo a `DELETE /activities/activity-5`
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5` y responde `y` a la confirmación
- **THEN** se realiza exactamente una petición `DELETE http://localhost:3000/activities/activity-5` con la cabecera `Authorization: Bearer tok-123`
- **AND** la salida contiene `Activity activity-5 deleted.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Borrado sin confirmación interactiva
- **GIVEN** una sesión válida y la API responde 204 a `DELETE /activities/activity-5`
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5 --yes`
- **THEN** no se pide confirmación
- **AND** la salida contiene `Activity activity-5 deleted.`
- **AND** el proceso termina con código de salida 0

### Requirement: Borrado cancelado
Si el usuario no confirma el borrado, el sistema SHALL indicarlo, no llamar a la API y terminar con
código 0. La respuesta por defecto de la confirmación SHALL ser «no».

#### Scenario: Usuario responde que no
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5` y responde `n`
- **THEN** la salida contiene `Deletion cancelled.`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

#### Scenario: Respuesta vacía
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5` y pulsa Intro sin responder
- **THEN** la salida contiene `Deletion cancelled.`
- **AND** no se realiza ninguna petición HTTP

### Requirement: Errores de validación de la API
Cuando la API rechaza un alta o una modificación con 400, el sistema SHALL mostrar el mensaje de la
API tras `Error:` y una línea por cada campo con error, y terminar con código 1.

#### Scenario: Fecha pasada y precio no válido
- **GIVEN** una sesión válida
- **AND** la API responde 400 a `POST /activities` con `{"message": "Validation failed", "errors": [{"field": "date", "message": "Date must be in the future"}, {"field": "price", "message": "Price must be greater than 0"}]}`
- **WHEN** el usuario ejecuta `activities create` con `--date 2020-01-01 --price 0` y el resto de opciones obligatorias
- **THEN** la salida de error contiene `Error: Validation failed`
- **AND** la salida de error contiene `date: Date must be in the future` y `price: Price must be greater than 0`
- **AND** el proceso termina con código de salida 1

#### Scenario: Mínimo mayor que el máximo en la modificación
- **GIVEN** una sesión válida
- **AND** la API responde 400 a `PUT /activities/activity-5` con `{"message": "Validation failed", "errors": [{"field": "minParticipants", "message": "Min participants cannot exceed max participants"}]}`
- **WHEN** el usuario ejecuta `activities update activity-5 --min-participants 20`
- **THEN** la salida de error contiene `Error: Validation failed` y `minParticipants: Min participants cannot exceed max participants`
- **AND** el proceso termina con código de salida 1

### Requirement: Actividad ajena o inexistente
Cuando la API responde 403 o 404 a una modificación o un borrado, el sistema SHALL mostrar el mensaje
de la API tras `Error:` y terminar con código 1.

#### Scenario: Modificar una actividad de otro usuario
- **GIVEN** una sesión válida
- **AND** la API responde 403 a `PUT /activities/activity-2` con `{"message": "You can only update your own activities", "errors": []}`
- **WHEN** el usuario ejecuta `activities update activity-2 --price 40`
- **THEN** la salida de error contiene `Error: You can only update your own activities`
- **AND** el proceso termina con código de salida 1

#### Scenario: Borrar una actividad de otro usuario
- **GIVEN** una sesión válida
- **AND** la API responde 403 a `DELETE /activities/activity-2` con `{"message": "You can only delete your own activities", "errors": []}`
- **WHEN** el usuario ejecuta `activities delete activity-2 --yes`
- **THEN** la salida de error contiene `Error: You can only delete your own activities`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad inexistente
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `DELETE /activities/activity-99` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activities delete activity-99 --yes`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** el proceso termina con código de salida 1

### Requirement: Fallos de comunicación al gestionar actividades
El sistema SHALL presentar los fallos de red, los errores 5xx y las respuestas correctas con forma
inesperada de `create`, `update` y `delete` como `Error: ...`, sin traza de Python y con código 1.

#### Scenario: API caída
- **GIVEN** una sesión válida y la conexión con la API es rechazada
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida de error contiene `Error: cannot connect to the API at http://localhost:3000`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Timeout
- **GIVEN** una sesión válida y la API no responde a tiempo
- **WHEN** el usuario ejecuta `activities update activity-5 --price 25`
- **THEN** la salida de error contiene `Error:` e indica que la API no respondió a tiempo
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno al borrar
- **GIVEN** una sesión válida
- **AND** la API responde 500 a `DELETE /activities/activity-5` con `{"message": "Failed to delete activity", "errors": []}`
- **WHEN** el usuario ejecuta `activities delete activity-5 --yes`
- **THEN** la salida de error contiene `Error: API error 500: Failed to delete activity`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta de alta incompleta
- **GIVEN** una sesión válida
- **AND** la API responde 201 a `POST /activities` con `{"message": "ok"}`
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida de error empieza por `Error: invalid response from the API`
- **AND** el proceso termina con código de salida 1
