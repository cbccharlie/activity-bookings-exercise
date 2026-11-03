# Design

## Context

Este change supone implementados los seis changes pendientes y reutiliza sus piezas:

- `add-user-registration`: `ApiClient._request()` y su traducción de errores (`ApiError` con
  `status_code`, `ApiConnectionError`, `ApiResponseError`; 5xx → `API error 500: <message>`).
- `add-activity-list`: `_request(..., params=...)`, el patrón de listado (`list_activities()`,
  tabla Rich con recuento singular/plural, `No ... found.`), `_format_date()` y `_format_price()`.
- `add-activity-management`: `ApiClient(..., token=...)`, `commands/_auth.py`
  (`authorized_client(settings)` y `login_hint()`).
- `add-activity-booking`: el grupo `bookings` en `commands/bookings_cmd.py`, el modelo `Booking`
  y `parse_booking()` (con `participants` entero y `paymentStatus` ausente → `pending`).

Contrato (`docs/api-reference.md`, `GET /bookings`, Reglas 6-7 y Discrepancias 7):

- Protegido. Query opcional `activityId`. Sin paginación.
- 200: array de `BookingResponse` = los campos de `Booking` más `activity` con `name`, `slug`,
  `price`, `date`, `duration`, `location` y `status` (sin `id`: el ID es `activityId`).
- 500 `Failed to retrieve bookings` para **todo** el listado si alguna reserva apunta a una
  actividad borrada.

El comportamiento exigido está en `specs/my-bookings/spec.md`.

## Goals / Non-Goals

**Goals:**
- Un subcomando fino que reutiliza el cliente autorizado, `parse_booking()` y el formateo de
  `activities list`.

**Non-Goals:**
- Pedir cada actividad con `GET /activities/:id`: la respuesta ya trae lo necesario.
- Recuperarse del 500 por actividad borrada (por ejemplo, listando reserva a reserva): la API no
  ofrece una forma de saber qué reserva falla.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py              # + BookingActivity, BookingSummary, parse_booking_summary(),
                             #   list_bookings()
  commands/bookings_cmd.py   # + subcomando `list`
  commands/_format.py        # (solo si hace falta) _format_date() y _format_price() compartidos
tests/
  test_api_client.py  test_bookings_cmd.py
```

`_format_date()` y `_format_price()` viven en `activities_cmd.py`. Si `bookings_cmd.py` ya los
importa de ahí (tras `add-activity-booking`), se sigue igual; si no, se mueven a
`commands/_format.py` sin cambiar su comportamiento. *Alternativa descartada:* duplicarlos.

### Modelo

- `BookingActivity`: dataclass frozen con `name: str`, `date: str`, `price: float` y `status: str`.
  Solo los campos que se muestran (YAGNI, como `Activity`).
- `BookingSummary`: dataclass frozen con `booking: Booking` y `activity: BookingActivity`.
  Compone el `Booking` existente en vez de repetir sus campos. *Alternativa descartada:* añadir
  `activity: BookingActivity | None` a `Booking`; obligaría a `create_booking()` a manejar un campo
  que su respuesta nunca trae.
- `parse_booking_summary(data, position) -> BookingSummary`: usa `parse_booking()` para la reserva
  y valida `activity` a mano (objeto; `name`, `date` y `status` cadenas; `price` `int`/`float` no
  `bool`). Fallo → `ApiResponseError("invalid response from the API: booking <id o posición> has
  no valid '<campo>'")`.

### Cliente de API

`ApiClient.list_bookings(activity_id: str | None = None) -> list[BookingSummary]`:

- `params = {"activityId": activity_id}` solo si hay `activity_id`; `_request("GET", "/bookings",
  params=params)`.
- Si el JSON no es una lista → `ApiResponseError("invalid response from the API: expected a list
  of bookings")`; si lo es, parsea cada elemento.

### Comando `bookings list`

```python
list_(ctx, activity: Annotated[str | None, typer.Option("--activity", metavar="ACTIVITY_ID")] = None)
```

Registrado con `@app.command("list")` (la función no puede llamarse `list`). Orden:

1. `--activity` en blanco → `typer.BadParameter("cannot be empty", param_hint="--activity")`
   (código 2). Se envía tras `strip()`.
2. `load_settings(ctx.obj)` → `authorized_client(settings)`.
3. `list_bookings()` dentro de `login_hint()` y de un segundo context manager pequeño,
   `_deleted_activity_hint()`, que convierte un `ApiError` con `status_code == 500` en
   `ActivityBookingsError(f"{exc}\nOne of your bookings may refer to a deleted activity.")`.
   *Alternativa descartada:* comprobar el mensaje `Failed to retrieve bookings`; el código basta y
   no depende del texto.
4. Salida. Usa `handle_errors`.

Presentación:

- Tabla Rich con título `My bookings` y columnas ID, Activity (`<name> (<activityId>)`), Date
  (`_format_date`), Seats (derecha), Total (`_format_price(price * participants)`, derecha),
  Payment y Activity status. Orden de la API.
- Recuento: `N bookings` / `1 booking`. Sin filas: `No bookings found.` y código 0.
- *Alternativa descartada:* una sola columna «Status» que combine pago y actividad; mezclaría dos
  conceptos y ocultaría que la reserva está pagada aunque la actividad se cancele.

Ejemplos:

```console
$ activity-bookings bookings list
                                     My bookings
 ID         Activity                     Date                  Seats   Total  Payment  Activity status
 booking-1  City Bike Tour (activity-2)  2026-12-20                2   70.00  paid     published
 booking-2  Yoga (activity-5)            2027-01-10 09:00 UTC      1   12.50  paid     confirmed
2 bookings

$ activity-bookings bookings list --activity activity-2
 ...
 booking-1  City Bike Tour (activity-2)  2026-12-20                2   70.00  paid     published
1 booking

$ activity-bookings bookings list
No bookings found.

$ activity-bookings bookings list --activity " "
Usage: activity-bookings bookings list [OPTIONS]
Error: Invalid value for '--activity': cannot be empty

$ activity-bookings bookings list
Error: API error 500: Failed to retrieve bookings
One of your bookings may refer to a deleted activity.

$ activity-bookings bookings list
Error: not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `parse_booking_summary` (completa, sin `paymentStatus`, sin
  `activity`, `activity` no objeto, `price` booleano, `name` ausente) y `list_bookings` con respx
  (ruta, cabecera con token, `activityId` presente/ausente, 200 vacío, respuesta no lista,
  elemento inválido, 401 y 500 como `ApiError` con su `status_code`).
- `tests/test_bookings_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`,
  reutilizando el fixture de sesión válida y el helper de JWT. Un helper nuevo construye reservas
  JSON con actividad y valores por defecto. Fechas de 2100 para no depender del reloj. «Sin
  petición HTTP» se comprueba con `respx_mock.calls` vacío; el parámetro con
  `route.calls.last.request.url.params`.

## Risks / Trade-offs

- [Una actividad borrada rompe todo el listado con 500 (Discrepancias 7)] → La CLI no puede
  esquivarlo; añade la causa probable al error para que el usuario no piense que la API está caída.
  Cualquier otro 500 recibirá la misma pista, que va formulada como posibilidad («may»).
- [El total lo calcula la CLI con el precio **actual** de la actividad; si el dueño lo cambió
  después, no coincide con lo cobrado] → La API no guarda el importe en la reserva. Se documenta en
  el README.
- [Una reserva con datos inválidos hace fallar todo el listado] → Mismo criterio que
  `activities list`: error claro con la reserva y el campo.
- [Depende de seis changes pendientes] → La tarea 1.1 lo comprueba. Hay que archivarlos antes, para
  que `auth-session` exista en `openspec/specs/`.
