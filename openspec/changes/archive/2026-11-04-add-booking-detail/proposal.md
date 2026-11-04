# Proposal

## Why

`bookings list` resume las reservas en una tabla, pero no deja consultar una reserva concreta por
su ID ni ver los datos que el listado omite (fecha de la reserva, ID del pago, lugar y duración de
la actividad). `GET /bookings/:id` devuelve la reserva propia con su actividad, y el change
`add-booking-list` ya dejaba `bookings show` para después.

## What Changes

- Nuevo subcomando `activity-bookings bookings show BOOKING_ID` en el grupo `bookings`:
  - Necesita sesión y reutiliza las comprobaciones de las rutas protegidas (sin sesión, sesión
    inválida o de otra API, token caducado y 401 con la sugerencia de `auth login`).
  - Muestra una ficha (tabla de dos columnas) con ID de la reserva, actividad (nombre e ID), fecha,
    duración y lugar de la actividad, plazas, precio por plaza, total (precio × plazas), estado
    del pago, ID del pago (si lo hay), estado de la actividad y fecha de la reserva.
  - Un ID vacío o en blanco es error de uso (código 2) sin llamar a la API.
  - Reserva inexistente o de otro usuario: `Error: Booking not found` con código 1 (la API no
    distingue ambos casos).
  - Errores de la API (500, en particular por actividad borrada, API caída, timeout, respuesta
    inesperada) como `Error: ...` con código 1.
- La capa de cliente de API gana `ApiClient.get_booking(booking_id)` y amplía el modelo de reserva
  con actividad para incluir los campos del detalle.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `my-bookings`: se añade el detalle de una reserva propia por su ID. La capacidad la crea
  `add-booking-list`, que ya anunciaba `bookings show`.

## Fuera de alcance

- Cancelar, modificar o borrar la reserva: la API no lo permite.
- Ver reservas de otros usuarios: la API responde 404.
- Buscar la reserva por actividad o por otro criterio distinto del ID (para eso está
  `bookings list --activity`).
- Consultar el pago por separado o mostrar el importe realmente cobrado: la API no lo expone en la
  reserva; el total se calcula con el precio actual.
- Pedir la actividad completa con `GET /activities/:id` (organizador, capacidad, etc.).
- Salida en JSON u otros formatos.

## Impact

- **Requisitos previos:** `add-booking-list` implementado (y con él los changes de los que
  depende: registro, login, listado y detalle de actividades, gestión de actividades y reserva).
- **Código:** `api_client.py` (`get_booking`, campos de detalle en el modelo de reserva con
  actividad) y `commands/bookings_cmd.py` (subcomando `show`).
- **Tests:** nuevos con respx. **Dependencias:** ninguna.
- **Documentación:** README (`bookings show`).
