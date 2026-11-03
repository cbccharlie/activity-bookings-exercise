# Design

## Context

Este change supone implementado `add-booking-list` (y los changes de los que depende). Reutiliza:

- `api_client.py`: `ApiClient(..., token=...)` y `_request()`, con su traducción de errores
  (4xx con JSON → `<message>`; 5xx → `API error <status>: <message>`; sin JSON válido → mensaje
  genérico con el código HTTP); `Booking` y `parse_booking()` (`paymentStatus` ausente →
  `pending`); `BookingActivity` (`name`, `date`, `price`, `status`), `BookingSummary`
  (`booking`, `activity`) y `parse_booking_summary()`.
- `commands/_auth.py`: `authorized_client(settings)` y `login_hint()`.
- `commands/bookings_cmd.py`: el grupo `bookings` y `_deleted_activity_hint()`.
- Formateo: `_format_date()`, `_format_price()` y `_format_duration()` (de `add-activity-detail`).
- `add-activity-detail`: el criterio de codificar el ID con `quote(id, safe="")` y la ficha Rich
  sin cabecera.

Contrato (`docs/api-reference.md`, `GET /bookings/:id` y Discrepancias 7):

- Protegido. 200 con un `BookingResponse`, igual que cada elemento de `GET /bookings`: campos de
  `Booking` (`paymentId` incluido) y `activity` con `name`, `slug`, `price`, `date`, `duration`,
  `location` y `status`.
- 404 `Booking not found` si no existe **o es de otro usuario**; 500 `Failed to retrieve booking`,
  también cuando la actividad de la reserva se ha borrado.

El comportamiento exigido está en `specs/my-bookings/spec.md`.

## Goals / Non-Goals

**Goals:**
- Un subcomando fino que reutiliza el cliente autorizado, el parseo del listado y el formateo.
- No cambiar el comportamiento de `bookings list` ni de `bookings create`.

**Non-Goals:**
- Buscar la reserva en `GET /bookings` como alternativa al 404 o al 500.
- Pedir `GET /activities/:id` para completar la ficha.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py              # + BookingDetail, parse_booking_detail(), get_booking()
  commands/bookings_cmd.py   # + subcomando `show`; _deleted_activity_hint() parametrizado
tests/
  test_api_client.py  test_bookings_cmd.py
```

### Modelo `BookingDetail`

Dataclass frozen que **compone** el `BookingSummary` del listado y añade los campos que solo
muestra el detalle: `summary: BookingSummary`, `payment_id: str | None`,
`activity_duration: int` y `activity_location: str`.

`parse_booking_detail(data: object) -> BookingDetail`:

- Si `data` no es un objeto JSON → `ApiResponseError("invalid response from the API: expected a
  booking")`.
- Llama a `parse_booking_summary(data, position=...)` y después valida a mano, con el mismo estilo
  de error (`booking <id> has no valid '<campo>'`):
  - `paymentId`: ausente o `null` → `None`; si existe, cadena.
  - `activity.location`: cadena.
  - `activity.duration`: `int` no `bool`; un `float` con valor entero se convierte a `int`, como en
    `ActivityDetail`.

*Alternativas descartadas:*
- Añadir `duration` y `location` a `BookingActivity`: el listado exigiría campos que no muestra y
  una reserva sin ellos rompería `bookings list`.
- Añadir `payment_id` a `Booking`: cambiaría `parse_booking()`, que comparte `create_booking()`.

### Cliente de API

`ApiClient.get_booking(booking_id: str) -> BookingDetail`: `_request("GET",
f"/bookings/{quote(booking_id, safe='')}")` y `parse_booking_detail()`. El 404 y el 401 llegan como
`ApiError` por la ruta genérica de `_request()`; no hace falta traducción específica.

### Comando `bookings show`

```python
show(ctx, booking_id: Annotated[str, typer.Argument(help="ID of the booking, e.g. booking-1.")])
```

Orden: Typer exige el argumento (código 2) → `booking_id.strip()` vacío →
`typer.BadParameter("BOOKING_ID cannot be empty", param_hint="BOOKING_ID")` (código 2) →
`load_settings(ctx.obj)` → `authorized_client(settings)` → `get_booking(booking_id.strip())`
dentro de `login_hint()` y `_deleted_activity_hint(...)` → ficha. Usa `handle_errors`.

`_deleted_activity_hint()` pasa a recibir el texto de la pista: el listado conserva
`One of your bookings may refer to a deleted activity.` y el detalle usa
`This booking may refer to a deleted activity.` *Alternativa descartada:* un segundo context
manager casi idéntico.

Presentación: tabla Rich sin cabecera (`show_header=False`, `box=None`), como `activities show`,
con la etiqueta en negrita y los valores sin markup:

| Fila | Valor |
|---|---|
| ID | ID de la reserva |
| Activity | `<name> (<activityId>)` |
| Date, Booked at | `_format_date()` de `activity.date` y de `createdAt` |
| Duration | `_format_duration()` → `120 min` |
| Location, Payment, Activity status | tal cual |
| Seats | entero |
| Price | `_format_price(price)` (por plaza) |
| Total | `_format_price(price * participants)` |
| Payment ID | solo si `paymentId` no es `None` |

Las etiquetas Seats, Total, Payment y Activity status coinciden con las columnas de `bookings list`.

Ejemplos:

```console
$ activity-bookings bookings show booking-1
ID               booking-1
Activity         City Bike Tour (activity-2)
Date             2026-12-20
Duration         120 min
Location         City Center
Seats            2
Price            35.00
Total            70.00
Payment          paid
Payment ID       payment-1
Activity status  published
Booked at        2026-11-03 10:00 UTC

$ activity-bookings bookings show booking-99
Error: Booking not found

$ activity-bookings bookings show booking-3
Error: API error 500: Failed to retrieve booking
This booking may refer to a deleted activity.

$ activity-bookings bookings show " "
Usage: activity-bookings bookings show [OPTIONS] BOOKING_ID
Error: Invalid value for BOOKING_ID: BOOKING_ID cannot be empty

$ activity-bookings bookings show booking-1
Error: not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `parse_booking_detail` (completa, sin `paymentId`, `paymentId`
  `null`, `duration` `120.0`, `duration` booleano, `location` ausente, no es un objeto) y
  `get_booking` con respx (ruta, ID codificado, cabecera con token, 404, 401 y 500 como `ApiError`
  con su `status_code`).
- `tests/test_bookings_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`,
  reutilizando el fixture de sesión válida, el helper de JWT y el helper de reservas JSON de
  `add-booking-list` (ampliado con `paymentId`, `duration` y `location` si no los tiene). Fechas de
  2100. «Sin petición HTTP» con `respx_mock.calls` vacío.

## Risks / Trade-offs

- [El 404 no distingue entre reserva inexistente y de otro usuario] → Se muestra el mensaje de la
  API tal cual; es un comportamiento deliberado del servidor para no revelar reservas ajenas.
- [El total usa el precio actual de la actividad, no el cobrado] → Igual que en `bookings list`; ya
  documentado en el README.
- [Cualquier 500 recibe la pista de actividad borrada] → Va formulada como posibilidad («may»).
- [Ediciones concurrentes de `bookings_cmd.py` y `api_client.py` con otros changes] → Cambios
  aditivos; la firma de `_deleted_activity_hint()` cambia, pero solo la usa `bookings list`.
- [Depende de `add-booking-list`] → La tarea 1.1 lo comprueba; hay que archivarlo antes, para que
  `my-bookings` exista en `openspec/specs/`.
