# Proposal

## Why

Una actividad recién creada queda en `draft` y no se puede reservar hasta que esté `published`,
pero la CLI no permite cambiar el estado: hay que llamar a `PATCH /activities/:id/status` a mano.
El change `add-activity-management` ya dejaba el cambio de estado para después.

## What Changes

- Nuevo subcomando `activity-bookings activities status ACTIVITY_ID NEW_STATUS` en el grupo
  `activities`:
  - `NEW_STATUS` es uno de `draft`, `published`, `confirmed`, `sold-out`, `done` o `cancelled`;
    otro valor es error de uso (código 2) sin llamar a la API. Un ID en blanco, también.
  - Necesita sesión y reutiliza las comprobaciones de las rutas protegidas (sin sesión, sesión de
    otra API, token caducado y 401 con la sugerencia de `auth login`).
  - Pasar a `cancelled` o `done`, estados finales, pide confirmación `[y/N]` (se salta con
    `--yes`/`-y`); el resto de estados se envían directamente.
  - Muestra `Activity <id> is now <status>.` y la actividad devuelta, como `create` y `update`.
  - Las transiciones no permitidas, la actividad ajena (403) o inexistente (404) y los demás
    errores de la API se muestran como `Error: ...` con código 1. La API indica en el mensaje las
    transiciones válidas.
- La capa de cliente de API gana `ApiClient.change_activity_status(activity_id, status)`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `activity-management`: se añade el cambio de estado de una actividad propia y `status` pasa a
  formar parte de los subcomandos del grupo.

## Fuera de alcance

- Validar en el cliente la máquina de estados o la propiedad: lo decide la API, que ya devuelve
  las transiciones válidas en el error; hacerlo en local exigiría pedir antes la actividad.
- Elegir el estado al crear o cambiarlo desde `activities update`.
- Subcomandos por transición (`publish`, `cancel`...) o un modo interactivo que ofrezca los estados
  posibles.
- Efectos del cambio de estado sobre reservas o pagos: la CLI no hace nada más que el `PATCH`.
- Salida en JSON u otros formatos.

## Impact

- **Requisitos previos:** `add-activity-management` (y con él la sesión en rutas protegidas).
- **Código:** `api_client.py` (`change_activity_status`) y `commands/activities_cmd.py`
  (subcomando `status`, reutilizando `ActivityStatus` y `_print_activity`).
- **Tests:** nuevos con respx. **Dependencias:** ninguna.
- **Documentación:** README (`activities status`) y, si el `api-explorer` encuentra diferencias,
  `docs/api-reference.md`.
