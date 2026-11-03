# Proposal

## Why

Un usuario con sesión solo puede consultar el catálogo; para organizar sus propias actividades
tiene que llamar a la API a mano. `POST`, `PUT` y `DELETE /activities` ya existen y exigen JWT, y
la sesión local de `auth register` / `auth login` ya guarda ese token. Este change es la primera
ruta protegida de la CLI y fija cómo se envía y se valida la sesión.

## What Changes

- Nuevos subcomandos en el grupo `activities`, todos con la sesión local:
  - `activities create`: crea una actividad con `--name`, `--price`, `--date`, `--location`,
    `--min-participants` y `--max-participants` (obligatorias) y `--duration` (opcional). La
    actividad queda en `draft` y a nombre del usuario de la sesión. Muestra la actividad creada.
  - `activities update ACTIVITY_ID`: modifica uno o varios de esos campos (al menos uno). Muestra
    la actividad actualizada.
  - `activities delete ACTIVITY_ID`: pide confirmación (se salta con `--yes`) y borra.
- Uso de la sesión en rutas protegidas, compartido por los próximos changes:
  - Sin sesión, con una sesión de otra `api_url` o con el token caducado según su `exp`, la CLI
    falla sin llamar a la API y sugiere `auth login`.
  - Un 401 del servidor también sugiere `auth login`.
- Se amplía el cliente de API con el envío del token y los métodos de alta, modificación y borrado.
- Errores de la API mostrados de forma clara: validación (400 con los campos), actividad ajena
  (403), inexistente (404), API caída, timeout y 5xx, con código 1.

## Capabilities

### New Capabilities

- `activity-management`: gestión de las actividades propias desde la CLI. En este change cubre
  alta, modificación y borrado; el cambio de estado se añadirá después.

### Modified Capabilities

- `auth-session`: se añade el uso de la sesión en las rutas protegidas (sesión ausente, de otra
  API o caducada, y 401 del servidor).

## Fuera de alcance

- Cambiar el estado (`PATCH /activities/:id/status`) y elegir el estado al crear.
- Listar solo "mis actividades" o ver el detalle de una actividad.
- Comprobar en el cliente la propiedad, las reglas de validación o si la actividad tiene reservas:
  lo decide el servidor.
- Prompts interactivos para los campos y salida en JSON.
- Renovar el token automáticamente.

## Impact

- **Requisitos previos:** `add-user-registration`, `add-user-login` (`load_session`,
  `token_expiry`) y `add-activity-list` (grupo `activities`, modelo `Activity` y formateo)
  implementados.
- **Código:** `api_client.py`, `session.py`, `commands/activities_cmd.py`.
- **Tests:** nuevos con respx. **Dependencias:** ninguna nueva.
- **Documentación:** README (uso de los tres subcomandos).
