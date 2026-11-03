# auth-session Specification

## Purpose

Define cómo guarda la CLI en local la sesión del usuario (el token JWT que devuelve la API y los
datos básicos del usuario): dónde se guarda, con qué formato y permisos, y cuándo se sustituye.

## Requirements

### Requirement: Guardado de la sesión tras el registro
Tras un registro correcto, el sistema SHALL guardar la sesión en el fichero JSON
`activity-bookings/session.json` dentro de `$XDG_CONFIG_HOME`, o de `~/.config` si esa variable no
está definida, creando el directorio si no existe.

#### Scenario: Sesión guardada en la ubicación por defecto
- **GIVEN** `XDG_CONFIG_HOME` no definida y el directorio `~/.config/activity-bookings` no existe
- **AND** la API responde 201 a `POST /users` con `accessToken` `tok-123`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** existe el fichero `~/.config/activity-bookings/session.json`

#### Scenario: Sesión guardada según XDG_CONFIG_HOME
- **GIVEN** `XDG_CONFIG_HOME=/tmp/cfg`
- **AND** la API responde 201 a `POST /users`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** existe el fichero `/tmp/cfg/activity-bookings/session.json`

### Requirement: Contenido de la sesión
El fichero de sesión SHALL contener un objeto JSON con `api_url` (la URL efectiva usada en el
registro), `access_token` y `user` con `id`, `username` y `email` tal como los devuelve la API.
No SHALL contener la contraseña.

#### Scenario: Contenido del fichero
- **GIVEN** la configuración efectiva usa `http://api.example.com`
- **AND** la API responde 201 con `{"user": {"id": 2, "username": "Ana", "email": "ana@example.com", "terms": true}, "accessToken": "tok-123"}`
- **WHEN** el usuario completa `activity-bookings auth register` con la contraseña `secret1`
- **THEN** el fichero de sesión contiene `"api_url": "http://api.example.com"`, `"access_token": "tok-123"` y `"user": {"id": 2, "username": "Ana", "email": "ana@example.com"}`
- **AND** el fichero no contiene `secret1`

### Requirement: Permisos del fichero de sesión
En sistemas POSIX, el sistema SHALL crear el fichero de sesión con permisos `0600` (solo lectura y
escritura para su propietario), también cuando sustituye uno existente.

#### Scenario: Permisos restringidos
- **GIVEN** un sistema POSIX
- **WHEN** el usuario completa `activity-bookings auth register` con éxito
- **THEN** los permisos del fichero de sesión son `0600`

### Requirement: Sustitución de la sesión existente
Un nuevo registro correcto SHALL sustituir por completo la sesión guardada. Un registro fallido
SHALL dejar intacta la sesión existente.

#### Scenario: Registro correcto con sesión previa
- **GIVEN** existe un fichero de sesión con `access_token` `old-token`
- **AND** la API responde 201 con `accessToken` `new-token`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** el fichero de sesión contiene `new-token` y no contiene `old-token`

#### Scenario: Registro fallido con sesión previa
- **GIVEN** existe un fichero de sesión con `access_token` `old-token`
- **AND** la API responde 400 a `POST /users`
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** el fichero de sesión sigue conteniendo `old-token`

### Requirement: Fallo al guardar la sesión
Si la cuenta se crea pero la sesión no se puede guardar, el sistema SHALL indicar con `Error:` que
la cuenta se ha creado pero la sesión no se ha guardado, incluyendo la ruta, y terminar con código 1.

#### Scenario: Directorio de sesión no escribible
- **GIVEN** la API responde 201 a `POST /users`
- **AND** la ruta del fichero de sesión no se puede escribir
- **WHEN** el usuario completa `activity-bookings auth register`
- **THEN** la salida de error contiene `Error:`, indica que la cuenta se ha creado y que no se pudo guardar la sesión, e incluye la ruta del fichero
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

### Requirement: Guardado de la sesión tras el login
Tras un login correcto, el sistema SHALL guardar la sesión en el mismo fichero, con el mismo
contenido y los mismos permisos que tras el registro, y sustituir por completo la sesión anterior.
Un login fallido SHALL dejar intacta la sesión existente.

#### Scenario: Contenido de la sesión tras el login
- **GIVEN** la configuración efectiva usa `http://api.example.com`
- **AND** la API responde 200 a `POST /login` con `{"user": {"id": 1, "username": "Mark Musk", "email": "m@f.c", "terms": true}, "accessToken": "tok-123"}`
- **WHEN** el usuario completa `activity-bookings auth login` con la contraseña `1234aB`
- **THEN** el fichero `$XDG_CONFIG_HOME/activity-bookings/session.json` contiene `"api_url": "http://api.example.com"`, `"access_token": "tok-123"` y `"user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"}`
- **AND** el fichero no contiene `1234aB`
- **AND** en un sistema POSIX sus permisos son `0600`

#### Scenario: Login correcto con sesión previa
- **GIVEN** existe un fichero de sesión con `access_token` `old-token`
- **AND** la API responde 200 a `POST /login` con `accessToken` `new-token`
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** el fichero de sesión contiene `new-token` y no contiene `old-token`

#### Scenario: Login fallido con sesión previa
- **GIVEN** existe un fichero de sesión con `access_token` `old-token`
- **AND** la API responde 401 a `POST /login`
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** el fichero de sesión sigue conteniendo `old-token`

### Requirement: Fallo al guardar la sesión tras el login
Si el login es correcto pero la sesión no se puede guardar, el sistema SHALL indicar con `Error:` que
el login ha funcionado pero la sesión no se ha guardado, incluyendo la ruta, y terminar con código 1.

#### Scenario: Directorio de sesión no escribible en el login
- **GIVEN** la API responde 200 a `POST /login`
- **AND** la ruta del fichero de sesión no se puede escribir
- **WHEN** el usuario completa `activity-bookings auth login`
- **THEN** la salida de error contiene `Error:`, indica que el login ha funcionado y que no se pudo guardar la sesión, e incluye la ruta del fichero
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

### Requirement: Cierre de la sesión local
El sistema SHALL ofrecer `activity-bookings auth logout`, que borra el fichero de sesión sin llamar a
la API, aunque su contenido no sea válido, e indica que la sesión se ha cerrado.

#### Scenario: Logout con sesión
- **GIVEN** existe un fichero de sesión válido
- **WHEN** el usuario ejecuta `activity-bookings auth logout`
- **THEN** el fichero de sesión ya no existe
- **AND** la salida contiene `Logged out`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

#### Scenario: Logout con un fichero de sesión corrupto
- **GIVEN** el fichero de sesión contiene `not json`
- **WHEN** el usuario ejecuta `activity-bookings auth logout`
- **THEN** el fichero de sesión ya no existe
- **AND** el proceso termina con código de salida 0

### Requirement: Logout sin sesión
Si no existe fichero de sesión, `auth logout` SHALL informar de que no hay sesión iniciada y terminar
con código de salida 0.

#### Scenario: Logout sin sesión
- **GIVEN** no existe fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings auth logout`
- **THEN** la salida contiene `Not logged in`
- **AND** el proceso termina con código de salida 0

### Requirement: Fallo al borrar la sesión
Si el fichero de sesión existe pero no se puede borrar, el sistema SHALL mostrar `Error:` con la ruta
del fichero y terminar con código de salida 1.

#### Scenario: Fichero de sesión no borrable
- **GIVEN** la ruta del fichero de sesión no se puede borrar
- **WHEN** el usuario ejecuta `activity-bookings auth logout`
- **THEN** la salida de error contiene `Error:` y la ruta del fichero de sesión
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

### Requirement: Consulta de la sesión actual
El sistema SHALL ofrecer `activity-bookings auth whoami`, que muestra a partir de la sesión local,
sin llamar a la API, el nombre de usuario, el email, la URL de la API y la caducidad del token. El
token no SHALL mostrarse.

#### Scenario: Sesión vigente
- **GIVEN** una sesión con `api_url` `http://api.example.com`, usuario `Mark Musk` y email `m@f.c`
- **AND** un token cuyo campo `exp` corresponde a una fecha futura
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida contiene `Mark Musk`, `m@f.c`, `http://api.example.com` y la fecha de caducidad en UTC
- **AND** la salida no contiene el token
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

### Requirement: Token caducado o ilegible en whoami
Si el token de la sesión ha caducado, `auth whoami` SHALL indicarlo y sugerir volver a iniciar
sesión. Si no se puede leer su caducidad, SHALL mostrarla como desconocida. En ambos casos termina
con código de salida 0.

#### Scenario: Token caducado
- **GIVEN** una sesión con un token cuyo campo `exp` corresponde a una fecha pasada
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida indica que el token ha caducado (`expired`) y sugiere `activity-bookings auth login`
- **AND** el proceso termina con código de salida 0

#### Scenario: Token sin caducidad legible
- **GIVEN** una sesión con `access_token` `tok-123`, que no es un JWT
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida indica que la caducidad es desconocida (`unknown`)
- **AND** el proceso termina con código de salida 0

### Requirement: Whoami sin sesión
Si no existe fichero de sesión, `auth whoami` SHALL mostrar `Error:` indicando que no hay sesión
iniciada y cómo iniciarla, y terminar con código de salida 1.

#### Scenario: Whoami sin sesión
- **GIVEN** no existe fichero de sesión
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida de error contiene `Error:` e indica que no hay sesión iniciada
- **AND** sugiere `activity-bookings auth login`
- **AND** el proceso termina con código de salida 1

### Requirement: Fichero de sesión inválido
Si el fichero de sesión no es JSON válido o le faltan campos, `auth whoami` SHALL mostrar `Error:` con
la ruta del fichero y la sugerencia de volver a iniciar sesión, y terminar con código de salida 1.

#### Scenario: Sesión que no es JSON
- **GIVEN** el fichero de sesión contiene `not json`
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida de error contiene `Error:`, la ruta del fichero de sesión y `activity-bookings auth login`
- **AND** la salida no contiene `Traceback`
- **AND** el proceso termina con código de salida 1

#### Scenario: Sesión sin access_token
- **GIVEN** el fichero de sesión contiene `{"api_url": "http://localhost:3000", "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"}}`
- **WHEN** el usuario ejecuta `activity-bookings auth whoami`
- **THEN** la salida de error contiene `Error:` y la ruta del fichero de sesión
- **AND** el proceso termina con código de salida 1
