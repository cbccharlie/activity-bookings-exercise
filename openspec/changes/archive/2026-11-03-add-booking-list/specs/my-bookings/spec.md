# Spec Delta

## Purpose

Permite a un usuario con sesión consultar desde la CLI sus propias reservas, con los datos de la
actividad reservada, el total pagado y el estado del pago y de la actividad.

## ADDED Requirements

### Requirement: Subcomando de listado de reservas
El sistema SHALL ofrecer el subcomando `activity-bookings bookings list`, dentro del grupo
`bookings`, con la opción `--activity ACTIVITY_ID`. Las peticiones se envían a
`GET /bookings` de la URL de la API de la configuración efectiva.

#### Scenario: Subcomando list en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings bookings --help`
- **THEN** la salida incluye los subcomandos `create` y `list`

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"` y una sesión de esa API
- **AND** la API responde 200 a `GET /bookings` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** se realiza la petición `GET http://api.example.com/bookings`
- **AND** el proceso termina con código de salida 0

### Requirement: Listado con sesión
El sistema SHALL exigir una sesión local válida para listar las reservas y SHALL enviar su token en
`Authorization: Bearer <token>`, aplicando las reglas de rutas protegidas de `auth-session`. Sin
sesión, con sesión inválida, de otra API o caducada no se llama a la API.

#### Scenario: Cabecera de autorización en el listado
- **GIVEN** una sesión con `access_token` `tok-123`
- **AND** la API responde 200 a `GET /bookings` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la petición `GET /bookings` lleva la cabecera `Authorization: Bearer tok-123`
- **AND** ni la salida estándar ni la de error contienen `tok-123`

#### Scenario: Listar sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Listar con la sesión caducada
- **GIVEN** un fichero de sesión cuyo token es un JWT con `exp` en el año 2000
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error:`, `expired` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Sesión de otra API al listar
- **GIVEN** un fichero de sesión con `api_url` `http://localhost:3000`
- **AND** un fichero de configuración con `api_url = "http://api.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error:`, `http://localhost:3000`, `http://api.example.com` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Token rechazado por el servidor al listar
- **GIVEN** una sesión válida
- **AND** la API responde 401 a `GET /bookings` con `{"message": "Invalid or expired token. Please login again.", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error: Invalid or expired token. Please login again.` y `activity-bookings auth login`
- **AND** el fichero de sesión sigue existiendo
- **AND** el proceso termina con código de salida 1

### Requirement: Tabla de reservas
El sistema SHALL mostrar las reservas en el orden que devuelve la API, en una tabla con el ID de la
reserva, la actividad (nombre e ID), su fecha, las plazas, el total (precio × plazas, con dos
decimales), el estado del pago y el estado de la actividad, seguida del recuento `N bookings`
(`1 booking` en singular).

#### Scenario: Varias reservas
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con dos reservas: `booking-1` de 2 plazas en `activity-2` (`City Bike Tour`, precio 35, fecha `2100-12-20`, estado `published`, pago `paid`) y `booking-2` de 1 plaza en `activity-5` (`Yoga`, precio 12.5, fecha `2100-01-10T09:00:00.000Z`, estado `confirmed`, pago `paid`)
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida contiene `booking-1`, `City Bike Tour`, `activity-2`, `2100-12-20`, `70.00`, `paid` y `published`
- **AND** la salida contiene `booking-2`, `Yoga`, `activity-5`, `2100-01-10 09:00 UTC`, `12.50` y `confirmed`
- **AND** `booking-1` aparece antes que `booking-2`
- **AND** la salida contiene `2 bookings`
- **AND** el proceso termina con código de salida 0

#### Scenario: Una reserva
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con una sola reserva
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida contiene `1 booking`
- **AND** la salida no contiene `1 bookings`

#### Scenario: Reserva sin estado de pago
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con una reserva sin el campo `paymentStatus`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida contiene `pending`
- **AND** el proceso termina con código de salida 0

#### Scenario: Sin reservas
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida contiene `No bookings found.`
- **AND** el proceso termina con código de salida 0

### Requirement: Filtro por actividad
Con `--activity ACTIVITY_ID`, el sistema SHALL enviar `activityId=<ACTIVITY_ID>` en la query de
`GET /bookings` y mostrar lo que devuelva la API. Sin la opción, no SHALL enviar `activityId`. Un
valor en blanco SHALL rechazarse como error de uso (código 2) sin llamar a la API.

#### Scenario: Filtrar por actividad
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings?activityId=activity-2` con una reserva de `activity-2`
- **WHEN** el usuario ejecuta `activity-bookings bookings list --activity activity-2`
- **THEN** la petición `GET /bookings` lleva el parámetro `activityId=activity-2`
- **AND** la salida contiene `activity-2`
- **AND** el proceso termina con código de salida 0

#### Scenario: Sin filtro no se envía activityId
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la petición `GET /bookings` no lleva el parámetro `activityId`

#### Scenario: Filtro sin resultados
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings?activityId=activity-99` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list --activity activity-99`
- **THEN** la salida contiene `No bookings found.`
- **AND** el proceso termina con código de salida 0

#### Scenario: Filtro en blanco
- **WHEN** el usuario ejecuta `activity-bookings bookings list --activity " "`
- **THEN** la salida de error menciona `--activity`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Errores del listado
Cuando el listado falla, el sistema SHALL mostrar `Error:` seguido del mensaje de la API (o de un
mensaje claro si no lo hay), sin `Traceback`, y terminar con código 1. Ante un 500 SHALL añadir que
una reserva puede apuntar a una actividad borrada, causa conocida de ese error en la API.

#### Scenario: Error interno por actividad borrada
- **GIVEN** una sesión válida
- **AND** la API responde 500 a `GET /bookings` con `{"message": "Failed to retrieve bookings", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error:`, `Failed to retrieve bookings` y `deleted activity`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta que no es una lista
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con `{"id": "booking-1"}`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error empieza por `Error:` e indica que la respuesta de la API no es válida
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Reserva incompleta en la respuesta
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con `[{"id": "booking-1", "activityId": "activity-2"}]`
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error empieza por `Error:` e indica que la respuesta de la API no es válida
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Servidor equivocado
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /bookings` con un cuerpo HTML
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error:` y `404`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: API caída
- **GIVEN** una sesión válida
- **AND** la API no acepta conexiones
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error contiene `Error:` y la URL de la API
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado al listar
- **GIVEN** una sesión válida
- **AND** la petición `GET /bookings` agota el tiempo de espera
- **WHEN** el usuario ejecuta `activity-bookings bookings list`
- **THEN** la salida de error empieza por `Error:`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1
