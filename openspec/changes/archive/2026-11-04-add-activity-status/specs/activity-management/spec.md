# Spec Delta

## MODIFIED Requirements

### Requirement: Subcomandos de gestión de actividades
El sistema SHALL ofrecer los subcomandos `create`, `update`, `delete` y `status` dentro del grupo
`activities`, junto al `list` existente.

#### Scenario: Subcomandos en la ayuda del grupo
- **WHEN** el usuario ejecuta `activity-bookings activities --help`
- **THEN** la salida contiene `list`, `create`, `update`, `delete` y `status`
- **AND** el proceso termina con código de salida 0

## ADDED Requirements

### Requirement: Cambio de estado de una actividad
El sistema SHALL cambiar el estado de una actividad con `activities status ACTIVITY_ID NEW_STATUS`,
enviando `PATCH <api_url>/activities/<ACTIVITY_ID>/status` con el token de la sesión, el ID
codificado para que no altere la ruta y el cuerpo JSON `{"status": "<NEW_STATUS>"}`. Tras una
respuesta correcta SHALL mostrar `Activity <id> is now <status>.` seguido de la actividad devuelta
(ID, nombre, fecha, lugar, precio, capacidad y estado).

#### Scenario: Publicar una actividad
- **GIVEN** una sesión válida para `http://localhost:3000` con `access_token` `tok-123`
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con la actividad `activity-5` (`Yoga`, estado `published`)
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** se realiza exactamente una petición `PATCH http://localhost:3000/activities/activity-5/status` con la cabecera `Authorization: Bearer tok-123`
- **AND** el cuerpo JSON es `{"status": "published"}`
- **AND** no se pide confirmación
- **AND** la salida contiene `Activity activity-5 is now published.` y `Yoga`
- **AND** ni la salida estándar ni la de error contienen `tok-123`
- **AND** el proceso termina con código de salida 0

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"` y una sesión de esa API
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con una actividad válida
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** se realiza la petición `PATCH http://api.example.com/activities/activity-5/status`
- **AND** el proceso termina con código de salida 0

#### Scenario: ID con caracteres especiales
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `PATCH /activities/a%2Fb/status` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status a/b published`
- **THEN** la petición se envía a la ruta `/activities/a%2Fb/status`
- **AND** el proceso termina con código de salida 1

### Requirement: Argumentos del cambio de estado
El sistema SHALL exigir `ACTIVITY_ID` y `NEW_STATUS`. `NEW_STATUS` SHALL ser uno de `draft`,
`published`, `confirmed`, `sold-out`, `done` o `cancelled`. Un argumento ausente, un ID en blanco o
un estado desconocido SHALL ser un error de uso con código 2, sin pedir confirmación ni llamar a la
API.

#### Scenario: Estado desconocido
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 open`
- **THEN** la salida de error menciona `NEW_STATUS` y `published`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Falta el estado
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5`
- **THEN** la salida de error menciona `NEW_STATUS`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Faltan el ID y el estado
- **WHEN** el usuario ejecuta `activity-bookings activities status`
- **THEN** la salida de error menciona `ACTIVITY_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: ID en blanco
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities status " " published`
- **THEN** la salida de error menciona `ACTIVITY_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Confirmación de los estados finales
Pasar a `cancelled` o `done`, estados de los que la actividad no puede salir, SHALL pedir
confirmación con respuesta por defecto «no», salvo con `--yes`/`-y`. Si el usuario no confirma, el
sistema SHALL mostrar `Status change cancelled.`, no llamar a la API y terminar con código 0. Los
demás estados no SHALL pedir confirmación. La confirmación SHALL pedirse después de comprobar la
sesión.

#### Scenario: Cancelación confirmada
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con la actividad en estado `cancelled`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 cancelled` y responde `y`
- **THEN** la salida contiene la pregunta de confirmación con `activity-5` y `cancelled`
- **AND** el cuerpo JSON enviado es `{"status": "cancelled"}`
- **AND** la salida contiene `Activity activity-5 is now cancelled.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Cancelación rechazada
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 cancelled` y responde `n`
- **THEN** la salida contiene `Status change cancelled.`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

#### Scenario: Respuesta vacía al pasar a done
- **GIVEN** una sesión válida
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 done` y pulsa Intro sin responder
- **THEN** la salida contiene `Status change cancelled.`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

#### Scenario: Estado final sin confirmación interactiva
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con la actividad en estado `done`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 done --yes`
- **THEN** no se pide confirmación
- **AND** la salida contiene `Activity activity-5 is now done.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Estado final sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 cancelled`
- **THEN** no se pide confirmación
- **AND** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Cambio de estado con sesión
El sistema SHALL exigir una sesión local válida para cambiar el estado, aplicando las reglas de
rutas protegidas de `auth-session`. Sin sesión, con sesión de otra API o caducada no se llama a la
API.

#### Scenario: Cambio de estado sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Cambio de estado con la sesión caducada
- **GIVEN** un fichero de sesión cuyo token es un JWT con `exp` en el año 2000
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error:`, `expired` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Sesión de otra API al cambiar el estado
- **GIVEN** un fichero de sesión con `api_url` `http://localhost:3000`
- **AND** un fichero de configuración con `api_url = "http://api.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error:`, `http://localhost:3000`, `http://api.example.com` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Token rechazado por el servidor al cambiar el estado
- **GIVEN** una sesión válida
- **AND** la API responde 401 a `PATCH /activities/activity-5/status` con `{"message": "Invalid or expired token. Please login again.", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error: Invalid or expired token. Please login again.` y `activity-bookings auth login`
- **AND** el fichero de sesión sigue existiendo
- **AND** el proceso termina con código de salida 1

### Requirement: Errores del cambio de estado
Cuando el cambio de estado falla, el sistema SHALL mostrar `Error:` seguido del mensaje de la API (o
de un mensaje claro si no lo hay), sin `Traceback`, y terminar con código 1. La CLI no SHALL validar
la transición: el mensaje de la API indica las transiciones válidas.

#### Scenario: Transición no permitida
- **GIVEN** una sesión válida
- **AND** la API responde 400 a `PATCH /activities/activity-5/status` con `{"message": "Invalid status transition from draft to done. Valid transitions are: published", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 done --yes`
- **THEN** la salida de error contiene `Error: Invalid status transition from draft to done. Valid transitions are: published`
- **AND** el proceso termina con código de salida 1

#### Scenario: Transición desde un estado final
- **GIVEN** una sesión válida
- **AND** la API responde 400 a `PATCH /activities/activity-5/status` con `{"message": "Invalid status transition from done to published. Valid transitions are: none (terminal state)", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error:` y `none (terminal state)`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad de otro usuario
- **GIVEN** una sesión válida
- **AND** la API responde 403 a `PATCH /activities/activity-2/status` con `{"message": "You can only transition your own activities", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-2 published`
- **THEN** la salida de error contiene `Error: You can only transition your own activities`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad inexistente
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `PATCH /activities/activity-99/status` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-99 published`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno al cambiar el estado
- **GIVEN** una sesión válida
- **AND** la API responde 500 a `PATCH /activities/activity-5/status` con `{"message": "Failed to transition activity status", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error: API error 500: Failed to transition activity status`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta incompleta
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con `{"message": "ok"}`
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error empieza por `Error: invalid response from the API`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Servidor equivocado
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `PATCH /activities/activity-5/status` con un cuerpo HTML
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error:` y `404`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: API caída al cambiar el estado
- **GIVEN** una sesión válida y la conexión con la API es rechazada
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error contiene `Error: cannot connect to the API at http://localhost:3000`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado al cambiar el estado
- **GIVEN** una sesión válida y la API no responde a tiempo
- **WHEN** el usuario ejecuta `activity-bookings activities status activity-5 published`
- **THEN** la salida de error empieza por `Error:` e indica que la API no respondió a tiempo
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1
