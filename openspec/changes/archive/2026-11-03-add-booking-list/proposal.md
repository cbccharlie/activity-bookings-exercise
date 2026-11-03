# Proposal

## Why

Con `bookings create` el usuario ya puede reservar, pero no tiene forma de ver qué ha reservado ni
en qué estado está. `GET /bookings` devuelve las reservas del usuario del token con los datos de la
actividad y el estado del pago, así que la CLI puede ofrecer el listado sin más llamadas.

## What Changes

- Nuevo subcomando `activity-bookings bookings list [--activity ACTIVITY_ID]` en el grupo
  `bookings`:
  - Necesita sesión y reutiliza las comprobaciones de las rutas protegidas (sin sesión, sesión
    inválida o de otra API, token caducado y 401 con la sugerencia de `auth login`).
  - `--activity`: envía `activityId` a la API para ver solo las reservas de esa actividad; en
    blanco es error de uso (código 2).
  - Muestra una tabla con ID de la reserva, actividad (nombre e ID), fecha, plazas, total
    (precio × plazas), estado del pago y estado de la actividad, en el orden que da la API, y un
    recuento (`N bookings`). Sin reservas: `No bookings found.` y código 0.
  - El «estado de la reserva» se muestra con dos columnas, pago y actividad, porque la API no
    tiene un estado de reserva propio.
  - Errores de la API (500, en particular el que provoca una actividad borrada, API caída,
    respuesta inesperada) como `Error: ...` con código 1.
- La capa de cliente de API gana el modelo `BookingSummary` (reserva con su actividad) y
  `ApiClient.list_bookings()`.

## Capabilities

### New Capabilities

- `my-bookings`: consultar desde la CLI las reservas propias, con los datos de su actividad y su
  estado.

### Modified Capabilities

Ninguna. Las reglas de rutas protegidas de `auth-session` se aplican sin cambios.

## Fuera de alcance

- Ver el detalle de una reserva (`GET /bookings/:id`): irá en un change posterior (`bookings show`).
- Cancelar, modificar o borrar reservas: la API no lo permite.
- Filtrar por estado del pago o de la actividad, ordenar o paginar en la CLI.
- Salida en JSON u otros formatos.
- Ver reservas de otros usuarios o de mis actividades: la API solo devuelve las del token.

## Impact

- **Requisitos previos:** `add-user-registration`, `add-user-login`, `add-activity-list`,
  `add-activity-detail`, `add-activity-management` y `add-activity-booking` implementados.
- **Código:** `api_client.py` y `commands/bookings_cmd.py` (nuevo subcomando `list`).
- **Tests:** nuevos con respx. **Dependencias:** ninguna.
- **Documentación:** README (`bookings list`).
