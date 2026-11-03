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
