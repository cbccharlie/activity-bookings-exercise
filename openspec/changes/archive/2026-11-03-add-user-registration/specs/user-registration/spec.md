# Spec Delta

## Purpose

Permite crear una cuenta de usuario en la API ActivityBookings desde la CLI con
`activity-bookings auth register`: qué datos se piden, qué se envía a la API, qué se muestra al
terminar y cómo se comunican los errores del registro.

## ADDED Requirements

### Requirement: Subcomando de registro
El sistema SHALL ofrecer el subcomando `activity-bookings auth register`, dentro de un grupo `auth`
que aparece en la ayuda raíz, y que envía `POST <api_url>/users` con un cuerpo JSON con `username`,
`email`, `password` y `terms`, usando la URL de la API de la configuración efectiva.

#### Scenario: Grupo auth en la ayuda
- **WHEN** el usuario ejecuta `activity-bookings --help`
- **THEN** la lista de subcomandos incluye `auth`
- **AND** `activity-bookings auth --help` muestra el subcomando `register`

#### Scenario: Petición enviada a la API configurada
- **GIVEN** un fichero de configuración con `api_url = "http://api.example.com"`
- **AND** la API responde 201 a `POST http://api.example.com/users`
- **WHEN** el usuario ejecuta `activity-bookings auth register --username Ana --email ana@example.com --accept-terms` e introduce `secret1` como contraseña y como confirmación
- **THEN** la API recibe un cuerpo JSON `{"username": "Ana", "email": "ana@example.com", "password": "secret1", "terms": true}`

#### Scenario: Configuración inválida
- **GIVEN** un fichero de configuración con `api_url = "ftp://example.com"`
- **WHEN** el usuario ejecuta `activity-bookings auth register`
- **THEN** la salida de error empieza por `Error:` e indica que `api_url` no es válida
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Entrada de los datos de registro
El sistema SHALL aceptar `--username` y `--email` como opciones y pedirlos de forma interactiva si
faltan. La contraseña SHALL pedirse siempre por prompt oculto con confirmación y nunca como opción.

#### Scenario: Datos pedidos de forma interactiva
- **GIVEN** la API responde 201 a `POST /users`
- **WHEN** el usuario ejecuta `activity-bookings auth register --accept-terms` e introduce `Ana`, `ana@example.com`, `secret1` y `secret1` en los prompts
- **THEN** la API recibe `username` `Ana`, `email` `ana@example.com` y `password` `secret1`
- **AND** el proceso termina con código de salida 0

#### Scenario: La contraseña no se muestra
- **GIVEN** la API responde 201 a `POST /users`
- **WHEN** el usuario completa el registro introduciendo `secret1` como contraseña
- **THEN** la salida no contiene `secret1`

#### Scenario: Confirmación de contraseña distinta
- **WHEN** el usuario introduce `secret1` como contraseña y `secret2` como confirmación
- **THEN** la CLI vuelve a pedir la contraseña
- **AND** no se realiza ninguna petición HTTP hasta que ambas coinciden

#### Scenario: No existe opción de contraseña
- **WHEN** el usuario ejecuta `activity-bookings auth register --password secret1`
- **THEN** la salida de error indica que la opción no existe
- **AND** el proceso termina con código de salida 2

### Requirement: Aceptación de los términos
El sistema SHALL enviar `terms: true` solo si el usuario acepta los términos, con `--accept-terms`
o confirmando un prompt. Si no los acepta, SHALL terminar con error sin llamar a la API.

#### Scenario: Términos aceptados en el prompt
- **GIVEN** la API responde 201 a `POST /users`
- **WHEN** el usuario ejecuta `activity-bookings auth register --username Ana --email ana@example.com`, introduce la contraseña y responde `y` a la pregunta de aceptación de términos
- **THEN** la API recibe `terms` `true`
- **AND** el proceso termina con código de salida 0

#### Scenario: Términos rechazados
- **WHEN** el usuario ejecuta `activity-bookings auth register --username Ana --email ana@example.com`, introduce la contraseña y responde `n` a la pregunta de aceptación de términos
- **THEN** la salida de error contiene `Error:` e indica que hay que aceptar los términos
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 1

### Requirement: Resultado de un registro correcto
Tras una respuesta 201, el sistema SHALL mostrar el nombre de usuario y el email devueltos por la
API, indicar que la sesión ha quedado iniciada y terminar con código de salida 0. El token no
SHALL mostrarse en la salida.

#### Scenario: Registro correcto
- **GIVEN** la API responde 201 con `{"user": {"id": 2, "username": "Ana", "email": "ana@example.com", "terms": true}, "accessToken": "tok-123"}`
- **WHEN** el usuario completa `activity-bookings auth register` con datos válidos
- **THEN** la salida contiene `Ana` y `ana@example.com`
- **AND** la salida indica que la sesión está iniciada (`Logged in`)
- **AND** la salida no contiene `tok-123`
- **AND** el proceso termina con código de salida 0

### Requirement: Errores de validación del servidor
Ante una respuesta 400, el sistema SHALL mostrar `Error:` con el `message` de la API seguido de
cada error de campo (`field: message`) y terminar con código de salida 1, sin guardar sesión.

#### Scenario: Varios campos inválidos
- **GIVEN** la API responde 400 con `{"message": "Validation failed", "errors": [{"field": "email", "message": "Email must be valid"}, {"field": "password", "message": "Password must be at least 6 characters"}]}`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error: Validation failed`
- **AND** contiene `email: Email must be valid` y `password: Password must be at least 6 characters`
- **AND** no se crea ni modifica el fichero de sesión
- **AND** el proceso termina con código de salida 1

#### Scenario: Email ya registrado
- **GIVEN** la API responde 400 con `{"message": "Email is already registered", "errors": [{"field": "email", "message": "Email is already registered"}]}`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error: Email is already registered`
- **AND** el proceso termina con código de salida 1

#### Scenario: Error 400 sin detalle de campos
- **GIVEN** la API responde 400 con `{"message": "Failed to register user", "errors": []}`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error: Failed to register user`
- **AND** el proceso termina con código de salida 1

### Requirement: Fallos de comunicación con la API
El sistema SHALL traducir los fallos de red y las respuestas inesperadas en un mensaje `Error:`
claro, sin traza de Python y con código de salida 1, sin guardar sesión.

#### Scenario: API caída
- **GIVEN** la conexión con `http://localhost:3000` es rechazada
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:` e indica que no se puede conectar con la API en `http://localhost:3000`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Tiempo de espera agotado
- **GIVEN** la petición a la API supera el tiempo de espera
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:` e indica que la API no ha respondido a tiempo
- **AND** el proceso termina con código de salida 1

#### Scenario: Error 5xx del servidor
- **GIVEN** la API responde 500 con `{"message": "Internal server error", "errors": []}`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:`, el código `500` y `Internal server error`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta de error que no es JSON
- **GIVEN** la API responde 400 con un cuerpo HTML
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:` y el código `400`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Respuesta correcta con formato inesperado
- **GIVEN** la API responde 201 con `{"user": {"id": 2}}` (sin `accessToken`)
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:` e indica que la respuesta de la API no es válida
- **AND** no se crea el fichero de sesión
- **AND** el proceso termina con código de salida 1
