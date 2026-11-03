# client-config Specification

## Purpose

Define cómo obtiene el cliente su configuración (la URL base de la API de ActivityBookings): dónde está el fichero de usuario, qué formato tiene, qué valores se usan por defecto, cómo se valida y cómo puede el usuario consultar la configuración efectiva.

## Requirements

### Requirement: Ubicación del fichero de configuración
El sistema SHALL leer la configuración del fichero TOML `activity-bookings/config.toml` dentro de `$XDG_CONFIG_HOME`, o de `~/.config` si esa variable no está definida. La opción global `--config <ruta>` SHALL sustituir esa ubicación.

#### Scenario: Ubicación por defecto
- **GIVEN** `XDG_CONFIG_HOME` no definida
- **AND** existe `~/.config/activity-bookings/config.toml` con `api_url = "http://api.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://api.example.com`

#### Scenario: Ubicación según XDG_CONFIG_HOME
- **GIVEN** `XDG_CONFIG_HOME=/tmp/cfg`
- **AND** existe `/tmp/cfg/activity-bookings/config.toml` con `api_url = "http://xdg.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://xdg.example.com`

#### Scenario: Ruta indicada con --config
- **GIVEN** existe `./custom.toml` con `api_url = "http://custom.example.com"`
- **WHEN** el usuario ejecuta `activity-bookings --config ./custom.toml config`
- **THEN** la URL de la API mostrada es `http://custom.example.com`

### Requirement: Valor por defecto sin fichero
El sistema SHALL usar `http://localhost:3000` como URL de la API cuando el fichero de configuración por defecto no existe o no define `api_url`, sin mostrar error.

#### Scenario: Fichero inexistente
- **GIVEN** no existe fichero de configuración en la ubicación por defecto
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://localhost:3000`
- **AND** el proceso termina con código de salida 0

#### Scenario: Fichero sin la clave api_url
- **GIVEN** el fichero de configuración existe pero no contiene `api_url`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://localhost:3000`

### Requirement: Fichero indicado explícitamente inexistente
El sistema SHALL tratar como error que la ruta indicada con `--config` no exista.

#### Scenario: --config apunta a un fichero inexistente
- **WHEN** el usuario ejecuta `activity-bookings --config ./no-existe.toml config`
- **THEN** la salida de error indica que el fichero de configuración no existe e incluye la ruta
- **AND** el proceso termina con código de salida 1

### Requirement: Validación de la configuración
El sistema SHALL rechazar un fichero que no sea TOML válido o cuyo `api_url` no sea una URL absoluta `http` o `https` con host, indicando la causa. Las claves desconocidas SHALL ignorarse.

#### Scenario: TOML mal formado
- **GIVEN** el fichero de configuración contiene `api_url = `
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la salida de error indica que el fichero no es TOML válido e incluye su ruta
- **AND** el proceso termina con código de salida 1

#### Scenario: URL no válida
- **GIVEN** el fichero de configuración contiene `api_url = "ftp://example.com"`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la salida de error indica que `api_url` no es una URL http(s) válida
- **AND** el proceso termina con código de salida 1

#### Scenario: api_url con tipo incorrecto
- **GIVEN** el fichero de configuración contiene `api_url = 3000`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la salida de error indica que `api_url` debe ser un texto
- **AND** el proceso termina con código de salida 1

#### Scenario: Claves desconocidas
- **GIVEN** el fichero contiene `api_url = "http://api.example.com"` y `foo = 1`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://api.example.com`
- **AND** el proceso termina con código de salida 0

### Requirement: Normalización de la URL
El sistema SHALL eliminar la barra final de `api_url` para que las rutas de la API se compongan de forma uniforme.

#### Scenario: URL con barra final
- **GIVEN** el fichero contiene `api_url = "http://api.example.com/"`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la URL de la API mostrada es `http://api.example.com`

### Requirement: Consulta de la configuración efectiva
El sistema SHALL ofrecer el subcomando `activity-bookings config` que muestra la URL de la API efectiva y su origen: la ruta del fichero del que se leyó o la indicación de que es el valor por defecto.

#### Scenario: Configuración desde fichero
- **GIVEN** un fichero de configuración válido en `<ruta>`
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la salida muestra la URL de la API y `<ruta>` como origen
- **AND** el proceso termina con código de salida 0

#### Scenario: Configuración por defecto
- **GIVEN** no existe fichero de configuración
- **WHEN** el usuario ejecuta `activity-bookings config`
- **THEN** la salida muestra `http://localhost:3000` e indica que es el valor por defecto
