# Spec Delta

## ADDED Requirements

### Requirement: Envío del token en las rutas protegidas
En los comandos que usan rutas protegidas de la API, el sistema SHALL enviar el `access_token` de la
sesión local en la cabecera `Authorization: Bearer <token>`, y no SHALL mostrar el token en la
salida.

#### Scenario: Cabecera de autorización
- **GIVEN** un fichero de sesión con `api_url` `http://localhost:3000` y `access_token` `tok-123`
- **AND** la API responde 204 a `DELETE /activities/activity-5`
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5 --yes`
- **THEN** la petición lleva la cabecera `Authorization: Bearer tok-123`
- **AND** ni la salida estándar ni la de error contienen `tok-123`

### Requirement: Ruta protegida sin sesión
Si no hay fichero de sesión, los comandos que usan rutas protegidas SHALL fallar con `Error:`,
sugerir `activity-bookings auth login`, no llamar a la API y terminar con código 1.

#### Scenario: Crear sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Borrar sin sesión no pide confirmación
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings activities delete activity-5`
- **THEN** no se pide confirmación
- **AND** la salida de error contiene `Error: not logged in`
- **AND** el proceso termina con código de salida 1

### Requirement: Ruta protegida con un fichero de sesión inválido
Si el fichero de sesión no es válido, los comandos que usan rutas protegidas SHALL fallar con
`Error:`, incluir la ruta del fichero y la sugerencia de `auth login`, no llamar a la API y terminar
con código 1.

#### Scenario: Sesión corrupta
- **GIVEN** el fichero de sesión contiene `not json`
- **WHEN** el usuario ejecuta `activities update activity-5 --price 25`
- **THEN** la salida de error contiene `Error:`, la ruta del fichero de sesión y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Sesión de otra API
Si la `api_url` guardada en la sesión no coincide con la de la configuración efectiva, los comandos
que usan rutas protegidas SHALL fallar con `Error:`, indicar las dos URL, sugerir `auth login`, no
llamar a la API y terminar con código 1.

#### Scenario: Configuración apuntando a otro servidor
- **GIVEN** un fichero de sesión con `api_url` `http://localhost:3000`
- **AND** un fichero de configuración con `api_url = "http://api.example.com"`
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida de error contiene `Error:`, `http://localhost:3000`, `http://api.example.com` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Token caducado en local
Si el `exp` del token de la sesión indica que ha caducado, los comandos que usan rutas protegidas
SHALL fallar con `Error:`, indicar que la sesión ha caducado, sugerir `auth login`, no llamar a la
API y terminar con código 1. Si la caducidad no se puede leer, SHALL enviar la petición igualmente.

#### Scenario: Token con exp pasado
- **GIVEN** un fichero de sesión cuyo token es un JWT con `exp` en el año 2000
- **WHEN** el usuario ejecuta `activities update activity-5 --price 25`
- **THEN** la salida de error contiene `Error:`, `expired` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

#### Scenario: Token sin caducidad legible
- **GIVEN** un fichero de sesión con `access_token` `tok-123`, que no es un JWT
- **AND** la API responde 200 a `PUT /activities/activity-5`
- **WHEN** el usuario ejecuta `activities update activity-5 --price 25`
- **THEN** se realiza la petición `PUT /activities/activity-5`
- **AND** el proceso termina con código de salida 0

### Requirement: Token rechazado por el servidor
Cuando la API responde 401 a una ruta protegida, el sistema SHALL mostrar el mensaje de la API tras
`Error:` seguido de la sugerencia de `activity-bookings auth login`, conservar el fichero de sesión
y terminar con código 1.

#### Scenario: Token inválido o caducado según el servidor
- **GIVEN** un fichero de sesión válido
- **AND** la API responde 401 a `POST /activities` con `{"message": "Invalid or expired token. Please login again.", "errors": []}`
- **WHEN** el usuario ejecuta `activities create` con las opciones obligatorias
- **THEN** la salida de error contiene `Error: Invalid or expired token. Please login again.` y `activity-bookings auth login`
- **AND** el fichero de sesión sigue existiendo
- **AND** el proceso termina con código de salida 1
