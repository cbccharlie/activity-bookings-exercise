# user-login Specification

## Purpose

Permite a un usuario con cuenta iniciar sesión en la API ActivityBookings desde la CLI con
`activity-bookings auth login`: qué datos se piden, qué se envía a la API, qué se muestra al
terminar y cómo se comunican los errores del login.

## Requirements

### Requirement: Subcomando de login
El sistema SHALL ofrecer el subcomando `activity-bookings auth login` dentro del grupo `auth`, que
envía `POST <api_url>/login` con un cuerpo JSON con `email` y `password`, usando la URL de la API de
la configuración efectiva.

#### Scenario: Login en la ayuda del grupo auth
- **WHEN** el usuario ejecuta `activity-bookings auth --help`
- **THEN** la salida muestra el subcomando `login`

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"`
- **AND** la API responde 200 a `POST http://api.example.com/login`
- **WHEN** el usuario ejecuta `activity-bookings auth login --email m@f.c` e introduce `1234aB` como contraseña
- **THEN** la API recibe un cuerpo JSON `{"email": "m@f.c", "password": "1234aB"}`

#### Scenario: Configuración inválida
- **GIVEN** un fichero de configuración con `api_url = "ftp://example.com"`
- **WHEN** el usuario ejecuta `activity-bookings auth login`
- **THEN** la salida de error empieza por `Error:` e indica que `api_url` no es válida
- **AND** no se pide la contraseña ni se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Entrada de las credenciales
El sistema SHALL aceptar `--email` como opción y pedirlo de forma interactiva si falta. La
contraseña SHALL pedirse siempre por prompt oculto, sin confirmación, y nunca como opción.

#### Scenario: Email pedido de forma interactiva
- **GIVEN** la API responde 200 a `POST /login`
- **WHEN** el usuario ejecuta `activity-bookings auth login` e introduce `m@f.c` y `1234aB` en los prompts
- **THEN** la API recibe `email` `m@f.c` y `password` `1234aB`
- **AND** el proceso termina con código de salida 0

#### Scenario: La contraseña no se muestra
- **GIVEN** la API responde 200 a `POST /login`
- **WHEN** el usuario completa el login introduciendo `1234aB` como contraseña
- **THEN** la salida no contiene `1234aB`

#### Scenario: No existe opción de contraseña
- **WHEN** el usuario ejecuta `activity-bookings auth login --password 1234aB`
- **THEN** la salida de error indica que la opción no existe
- **AND** el proceso termina con código de salida 2

### Requirement: Resultado de un login correcto
Tras una respuesta 200, el sistema SHALL mostrar el nombre de usuario y el email devueltos por la
API, indicar que la sesión ha quedado iniciada y terminar con código de salida 0. El token no SHALL
mostrarse en la salida.

#### Scenario: Login correcto
- **GIVEN** la API responde 200 con `{"user": {"id": 1, "username": "Mark Musk", "email": "m@f.c", "terms": true}, "accessToken": "tok-123"}`
- **WHEN** el usuario completa `activity-bookings auth login` con credenciales válidas
- **THEN** la salida contiene `Mark Musk` y `m@f.c`
- **AND** la salida indica que la sesión está iniciada (`Logged in`)
- **AND** la salida no contiene `tok-123`
- **AND** el proceso termina con código de salida 0

### Requirement: Credenciales rechazadas
Ante una respuesta 401, el sistema SHALL mostrar `Error:` con el `message` de la API y terminar con
código de salida 1, sin guardar sesión.

#### Scenario: Email o contraseña incorrectos
- **GIVEN** la API responde 401 con `{"message": "Invalid email or password", "errors": []}`
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error: Invalid email or password`
- **AND** no se crea ni modifica el fichero de sesión
- **AND** el proceso termina con código de salida 1

#### Scenario: Fallo de autenticación genérico
- **GIVEN** la API responde 401 con `{"message": "Authentication failed", "errors": []}`
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error: Authentication failed`
- **AND** el proceso termina con código de salida 1

### Requirement: Errores de validación del login
Ante una respuesta 400, el sistema SHALL mostrar `Error:` con el `message` de la API seguido de cada
error de campo (`field: message`) y terminar con código de salida 1, sin guardar sesión.

#### Scenario: Email vacío
- **GIVEN** la API responde 400 con `{"message": "Validation failed", "errors": [{"field": "email", "message": "Email is required and must be a non-empty string"}]}`
- **WHEN** el usuario ejecuta `activity-bookings auth login --email ""` e introduce una contraseña
- **THEN** la salida de error contiene `Error: Validation failed`
- **AND** contiene `email: Email is required and must be a non-empty string`
- **AND** el proceso termina con código de salida 1

### Requirement: Fallos de comunicación en el login
El sistema SHALL traducir los fallos de red y las respuestas inesperadas del login en un mensaje
`Error:` claro, sin traza de Python y con código de salida 1, sin guardar sesión.

#### Scenario: API caída
- **GIVEN** la conexión con `http://localhost:3000` es rechazada
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error:` e indica que no se puede conectar con la API en `http://localhost:3000`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado
- **GIVEN** la petición a la API supera el tiempo de espera
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error:` e indica que la API no ha respondido a tiempo
- **AND** el proceso termina con código de salida 1

#### Scenario: Error 5xx del servidor
- **GIVEN** la API responde 500 con `{"message": "Internal server error", "errors": []}`
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error:`, el código `500` y `Internal server error`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta correcta con formato inesperado
- **GIVEN** la API responde 200 con `{"user": {"id": 1}}` (sin `accessToken`)
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error:` e indica que la respuesta de la API no es válida
- **AND** no se crea el fichero de sesión
- **AND** el proceso termina con código de salida 1
