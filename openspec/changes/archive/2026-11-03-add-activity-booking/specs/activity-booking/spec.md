# Spec Delta

## Purpose

Permite a un usuario con sesión reservar plazas en una actividad abierta desde la CLI, confirmando
antes el importe que se va a cobrar y con errores de la API traducidos a mensajes claros.

## ADDED Requirements

### Requirement: Subcomando de reserva
El sistema SHALL ofrecer el subcomando `activity-bookings bookings create ACTIVITY_ID`, dentro del
grupo `bookings`, con la opción `--participants` / `-p` (entero, 1 por defecto) y la opción
`--yes` / `-y`. Las peticiones se envían a la URL de la API de la configuración efectiva.

#### Scenario: Grupo bookings en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings --help`
- **THEN** la salida incluye el grupo `bookings`

#### Scenario: Subcomando create en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings bookings --help`
- **THEN** la salida incluye el subcomando `create`

#### Scenario: Reserva con el número de plazas por defecto
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /activities/activity-2` con una actividad `published`, de fecha `2100-12-20` y precio 35
- **AND** la API responde 201 a `POST /bookings` con una reserva `booking-1` de 1 plaza
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** el cuerpo enviado a `POST /bookings` es `{"activityId": "activity-2", "participants": 1}`
- **AND** el proceso termina con código de salida 0

#### Scenario: Reserva con varias plazas
- **GIVEN** una sesión válida y la actividad `activity-2` reservable con precio 35
- **AND** la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 -p 2 -y`
- **THEN** el cuerpo enviado a `POST /bookings` es `{"activityId": "activity-2", "participants": 2}`
- **AND** `participants` se envía como número entero, no como cadena

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"` y una sesión de esa API
- **AND** la actividad `activity-2` es reservable y la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** se realizan `GET http://api.example.com/activities/activity-2` y `POST http://api.example.com/bookings`

### Requirement: Validación de la entrada
El sistema SHALL rechazar como error de uso (código 2), sin llamar a la API, un `ACTIVITY_ID` ausente
o en blanco y un `--participants` que no sea un entero de 1 o más.

#### Scenario: Sin ID
- **WHEN** el usuario ejecuta `activity-bookings bookings create`
- **THEN** la salida de error indica que falta el argumento `ACTIVITY_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: ID vacío
- **WHEN** el usuario ejecuta `activity-bookings bookings create " " --yes`
- **THEN** la salida de error indica que `ACTIVITY_ID` no puede estar vacío
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Cero plazas
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --participants 0 --yes`
- **THEN** la salida de error menciona `--participants`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Plazas no enteras
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --participants 1.5 --yes`
- **THEN** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Reserva con sesión
El sistema SHALL exigir una sesión local válida para reservar y SHALL enviar su token en
`Authorization: Bearer <token>` en `POST /bookings`, aplicando las reglas de rutas protegidas de
`auth-session`. Sin sesión, con sesión inválida, de otra API o caducada no se llama a la API.

#### Scenario: Cabecera de autorización en la reserva
- **GIVEN** una sesión con `access_token` `tok-123`
- **AND** la actividad `activity-2` es reservable y la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la petición `POST /bookings` lleva la cabecera `Authorization: Bearer tok-123`
- **AND** ni la salida estándar ni la de error contienen `tok-123`

#### Scenario: Reservar sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2`
- **THEN** no se pide confirmación
- **AND** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Reservar con la sesión caducada
- **GIVEN** un fichero de sesión cuyo token es un JWT con `exp` en el año 2000
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error:`, `expired` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Token rechazado por el servidor al reservar
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 401 a `POST /bookings` con `{"message": "Invalid or expired token. Please login again.", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error: Invalid or expired token. Please login again.` y `activity-bookings auth login`
- **AND** el fichero de sesión sigue existiendo
- **AND** el proceso termina con código de salida 1

### Requirement: Solo actividades abiertas
Antes de reservar, el sistema SHALL consultar `GET /activities/<ACTIVITY_ID>` y SHALL rechazar con
`Error:` y código 1, sin llamar a `POST /bookings`, una actividad cuyo estado no sea `published` o
cuya fecha ya haya pasado. Una fecha sin hora cuenta como no pasada durante todo ese día (UTC).

#### Scenario: Actividad en borrador
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /activities/activity-4` con una actividad de estado `draft` y fecha `2100-03-01T09:00:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-4 --yes`
- **THEN** la salida de error contiene `Error:`, `activity-4`, `not open for booking` y `draft`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad cancelada
- **GIVEN** una sesión válida y la actividad `activity-2` con estado `cancelled` y fecha futura
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `not open for booking` y `cancelled`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad ya pasada
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /activities/activity-3` con una actividad `published` y fecha `2000-08-25T14:00:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-3 --yes`
- **THEN** la salida de error contiene `Error:`, `activity-3` y `already took place`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad de hoy sin hora
- **GIVEN** una sesión válida y la fecha actual es 2026-12-20 a las 23:00 UTC
- **AND** la actividad `activity-2` está `published` con fecha `2026-12-20`
- **AND** la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** se realiza la petición `POST /bookings`
- **AND** el proceso termina con código de salida 0

#### Scenario: Fecha ilegible
- **GIVEN** una sesión válida y la actividad `activity-2` está `published` con fecha `pronto`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error:` y `activity-2`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad inexistente
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /activities/activity-99` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-99 --yes`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 1

### Requirement: Confirmación del cobro
Sin `--yes`, el sistema SHALL pedir confirmación (por defecto, no) mostrando el nombre y el ID de la
actividad, su fecha, las plazas y el total (precio × plazas, con dos decimales) antes de
`POST /bookings`. Si el usuario no confirma, SHALL mostrar `Booking cancelled.`, no reservar y
terminar con código 0.

#### Scenario: Confirmación aceptada
- **GIVEN** una sesión válida y la actividad `activity-2` (`City Bike Tour`) reservable con precio 35
- **AND** la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 -p 2` y responde `y`
- **THEN** la pregunta contiene `City Bike Tour`, `activity-2`, `2` y `70.00`
- **AND** se realiza la petición `POST /bookings`
- **AND** el proceso termina con código de salida 0

#### Scenario: Confirmación rechazada
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2` y responde `n`
- **THEN** la salida contiene `Booking cancelled.`
- **AND** no se realiza ninguna petición `POST /bookings`
- **AND** el proceso termina con código de salida 0

#### Scenario: Sin confirmación con --yes
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 201 a `POST /bookings`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes` sin entrada
- **THEN** no se muestra ninguna pregunta
- **AND** el proceso termina con código de salida 0

### Requirement: Resultado de la reserva
Tras una reserva correcta, el sistema SHALL mostrar `Booking <id> created.` y una ficha con el ID de
la reserva, la actividad (nombre e ID), su fecha, las plazas, el total con dos decimales y el estado
del pago devuelto por la API.

#### Scenario: Ficha de la reserva
- **GIVEN** una sesión válida y la actividad `activity-2` (`City Bike Tour`) reservable con precio 35 y fecha `2100-12-20`
- **AND** la API responde 201 a `POST /bookings` con `{"id": "booking-1", "activityId": "activity-2", "userId": "user-1", "participants": 2, "createdAt": "2026-11-03T10:00:00.000Z", "paymentId": "payment-1", "paymentStatus": "paid"}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 -p 2 --yes`
- **THEN** la salida contiene `Booking booking-1 created.`, `City Bike Tour`, `activity-2`, `2100-12-20`, `70.00` y `paid`
- **AND** el proceso termina con código de salida 0

#### Scenario: Respuesta de reserva incompleta
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 201 a `POST /bookings` con `{"activityId": "activity-2"}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error empieza por `Error:` e indica que la respuesta de la API no es válida
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

### Requirement: Errores de la reserva
Cuando la reserva falla, el sistema SHALL mostrar `Error:` seguido del mensaje de la API (o de un
mensaje claro si no lo hay), sin `Traceback`, y terminar con código 1.

#### Scenario: Capacidad superada
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 400 a `POST /bookings` con `{"message": "Capacity exceeded. Available: 13, Requested: 20", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 -p 20 --yes`
- **THEN** la salida de error contiene `Error: Capacity exceeded. Available: 13, Requested: 20`
- **AND** el proceso termina con código de salida 1

#### Scenario: Error de validación de la API
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 400 a `POST /bookings` con `{"message": "Validation failed", "errors": [{"field": "participants", "message": "Participants is required and must be a positive number (at least 1)"}]}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error: Validation failed`, `participants` y `at least 1`
- **AND** el proceso termina con código de salida 1

#### Scenario: Pago rechazado
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 402 a `POST /bookings` con `{"message": "Payment could not be processed", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error: Payment could not be processed`
- **AND** el proceso termina con código de salida 1

#### Scenario: Actividad borrada entre la consulta y la reserva
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 404 a `POST /bookings` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno al reservar
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la API responde 500 a `POST /bookings` con `{"message": "Internal error", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error:` y `500`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: API caída
- **GIVEN** una sesión válida
- **AND** la API no acepta conexiones
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error contiene `Error:` y la URL de la API
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado al reservar
- **GIVEN** una sesión válida y la actividad `activity-2` reservable
- **AND** la petición `POST /bookings` agota el tiempo de espera
- **WHEN** el usuario ejecuta `activity-bookings bookings create activity-2 --yes`
- **THEN** la salida de error empieza por `Error:`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1
