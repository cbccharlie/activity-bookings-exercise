# Proposal

## Why

La CLI permite registrarse, iniciar sesión y explorar actividades, pero aún no deja apuntarse a
ninguna, que es el objetivo del producto. `POST /bookings` reserva y cobra en el acto, y el servidor
no comprueba el estado ni la fecha de la actividad: la CLI debe evitar reservas en actividades no
abiertas y confirmar el cobro.

## What Changes

- Nuevo grupo `bookings` con
  `activity-bookings bookings create ACTIVITY_ID [--participants N] [--yes]`:
  - `--participants` / `-p`: entero de 1 o más; por defecto, 1.
  - Necesita sesión y reutiliza las comprobaciones de las rutas protegidas (sin sesión, sesión
    inválida o de otra API, token caducado y 401 con la sugerencia de `auth login`).
  - Consulta antes `GET /activities/:id` y solo sigue si la actividad está `published` y su fecha no
    ha pasado; si no, `Error:` sin llamar a `POST /bookings`.
  - Pide confirmación con actividad, fecha, plazas y total (precio × plazas); `--yes` / `-y` la
    omite. Si se rechaza, no reserva y termina con código 0.
  - Si va bien, muestra la reserva: ID, actividad, plazas, total y estado del pago.
  - Errores de la API (capacidad superada, pago rechazado, actividad inexistente, API caída, 5xx,
    respuesta inesperada) como `Error: ...` con código 1.
- La capa de cliente de API gana el modelo `Booking` y `ApiClient.create_booking()`.

## Capabilities

### New Capabilities

- `activity-booking`: reservar plazas en una actividad desde la CLI, con comprobaciones previas,
  confirmación del cobro y traducción de errores.

### Modified Capabilities

Ninguna. Las reglas de rutas protegidas de `auth-session` se aplican sin cambios.

## Fuera de alcance

- Consultar mis reservas (`GET /bookings`): irá en un change posterior.
- Cancelar o modificar reservas: la API no lo permite.
- Mostrar plazas libres: la API no las expone; se confía en su 400 `Capacity exceeded`.
- Impedir reservar actividades propias o comprobar `minParticipants`.
- Método de pago o moneda.
- Reservar por `slug` o nombre.

## Impact

- **Requisitos previos:** `add-user-registration`, `add-user-login`, `add-activity-list`,
  `add-activity-detail` y `add-activity-management` implementados.
- **Código:** `api_client.py`, nuevo `commands/bookings_cmd.py` y su registro en `cli.py`.
- **Tests:** nuevos con respx. **Dependencias:** ninguna.
- **Documentación:** README (`bookings create`).
