# Spec Delta

## ADDED Requirements

### Requirement: Subcomando de detalle de reserva
El sistema SHALL ofrecer el subcomando `activity-bookings bookings show BOOKING_ID`, dentro del
grupo `bookings`. La petición se envía a `GET /bookings/<BOOKING_ID>` de la URL de la API de la
configuración efectiva, con el ID codificado para que no altere la ruta.

#### Scenario: Subcomando show en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings bookings --help`
- **THEN** la salida incluye los subcomandos `create`, `list` y `show`

#### Scenario: Petición de detalle enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"` y una sesión de esa API
- **AND** la API responde 200 a `GET /bookings/booking-1` con una reserva válida
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** se realiza la petición `GET http://api.example.com/bookings/booking-1`
- **AND** el proceso termina con código de salida 0

#### Scenario: ID con caracteres especiales
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /bookings/a%2Fb` con `{"message": "Booking not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings show a/b`
- **THEN** la petición se envía a la ruta `/bookings/a%2Fb`
- **AND** el proceso termina con código de salida 1

#### Scenario: ID de reserva en blanco
- **WHEN** el usuario ejecuta `activity-bookings bookings show " "`
- **THEN** la salida de error menciona `BOOKING_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

#### Scenario: Sin ID de reserva
- **WHEN** el usuario ejecuta `activity-bookings bookings show`
- **THEN** la salida de error menciona `BOOKING_ID`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 2

### Requirement: Detalle con sesión
El sistema SHALL exigir una sesión local válida para ver el detalle de una reserva y SHALL enviar
su token en `Authorization: Bearer <token>`, aplicando las reglas de rutas protegidas de
`auth-session`. Sin sesión, con sesión inválida, de otra API o caducada no se llama a la API.

#### Scenario: Cabecera de autorización en el detalle
- **GIVEN** una sesión con `access_token` `tok-123`
- **AND** la API responde 200 a `GET /bookings/booking-1` con una reserva válida
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la petición lleva la cabecera `Authorization: Bearer tok-123`
- **AND** ni la salida estándar ni la de error contienen `tok-123`

#### Scenario: Detalle sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Detalle con la sesión caducada
- **GIVEN** un fichero de sesión cuyo token es un JWT con `exp` en el año 2000
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error:`, `expired` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Sesión de otra API al ver el detalle
- **GIVEN** un fichero de sesión con `api_url` `http://localhost:3000`
- **AND** un fichero de configuración con `api_url = "http://api.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error:`, `http://localhost:3000`, `http://api.example.com` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Token rechazado por el servidor al ver el detalle
- **GIVEN** una sesión válida
- **AND** la API responde 401 a `GET /bookings/booking-1` con `{"message": "Invalid or expired token. Please login again.", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error: Invalid or expired token. Please login again.` y `activity-bookings auth login`
- **AND** el fichero de sesión sigue existiendo
- **AND** el proceso termina con código de salida 1

### Requirement: Ficha de la reserva
El sistema SHALL mostrar la reserva como una ficha de pares campo-valor con: ID, actividad (nombre
e ID), fecha, duración y lugar de la actividad, plazas, precio por plaza y total (precio × plazas)
con dos decimales, estado del pago, ID del pago si existe, estado de la actividad y fecha de la
reserva.

#### Scenario: Reserva completa
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings/booking-1` con la reserva `booking-1` de 2 plazas en `activity-2` (`City Bike Tour`, precio 35, fecha `2100-12-20`, duración 120, lugar `City Center`, estado `published`), pago `payment-1` con estado `paid` y `createdAt` `2100-11-03T10:00:00.000Z`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida contiene `booking-1`, `City Bike Tour`, `activity-2`, `2100-12-20`, `120 min` y `City Center`
- **AND** la salida contiene `35.00`, `70.00`, `paid`, `payment-1`, `published` y `2100-11-03 10:00 UTC`
- **AND** el proceso termina con código de salida 0

#### Scenario: Reserva sin estado de pago
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings/booking-1` con una reserva sin los campos `paymentStatus` ni `paymentId`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida contiene `pending`
- **AND** la salida no contiene `Payment ID`
- **AND** el proceso termina con código de salida 0

### Requirement: Errores del detalle de reserva
Cuando el detalle falla, el sistema SHALL mostrar `Error:` seguido del mensaje de la API (o de un
mensaje claro si no lo hay), sin `Traceback`, y terminar con código 1. Ante un 500 SHALL añadir que
la reserva puede apuntar a una actividad borrada, causa conocida de ese error en la API.

#### Scenario: Reserva inexistente o de otro usuario
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /bookings/booking-99` con `{"message": "Booking not found", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-99`
- **THEN** la salida de error contiene `Error: Booking not found`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Error interno al ver el detalle
- **GIVEN** una sesión válida
- **AND** la API responde 500 a `GET /bookings/booking-1` con `{"message": "Failed to retrieve booking", "errors": []}`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error:`, `Failed to retrieve booking` y `deleted activity`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta que no es un objeto
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings/booking-1` con `[]`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error empieza por `Error:` e indica que la respuesta de la API no es válida
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Reserva incompleta en el detalle
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings/booking-1` con `{"id": "booking-1", "activityId": "activity-2"}`
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error empieza por `Error:` e indica que la respuesta de la API no es válida
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Servidor equivocado al ver el detalle
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /bookings/booking-1` con un cuerpo HTML
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error:` y `404`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: API caída al ver el detalle
- **GIVEN** una sesión válida
- **AND** la API no acepta conexiones
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error contiene `Error:` y la URL de la API
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado al ver el detalle
- **GIVEN** una sesión válida
- **AND** la petición `GET /bookings/booking-1` agota el tiempo de espera
- **WHEN** el usuario ejecuta `activity-bookings bookings show booking-1`
- **THEN** la salida de error empieza por `Error:`
- **AND** no se muestra ningún `Traceback`
- **AND** el proceso termina con código de salida 1
