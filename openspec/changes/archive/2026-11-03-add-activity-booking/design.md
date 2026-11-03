# Design

## Context

Este change supone implementados los cinco changes pendientes y reutiliza sus piezas:

- `add-user-registration`: `ApiClient` y `_request()`, con la traducción de errores (`ApiError`
  con `status_code` y `field_errors`, `ApiConnectionError` y `ApiResponseError`).
- `add-activity-list`: el modelo `Activity` (`id`, `name`, `date`, `location`, `price`,
  `max_participants`, `status`), `_format_date()` y `_format_price()`.
- `add-activity-detail`: `ApiClient.get_activity(activity_id) -> ActivityDetail` (que compone un
  `Activity`), con el ID ya codificado.
- `add-activity-management`: `ApiClient(..., token=...)`, `require_session()`,
  `commands/_auth.py` (`authorized_client(settings)` y `login_hint()`) y el patrón de confirmación
  con `--yes` de `activities delete`.

Contrato (`docs/api-reference.md`, `POST /bookings` y Reglas 1-3 y 5-6):

- Cuerpo `{activityId: string, participants: number}`; `participants` tiene que ser `number`.
- Orden: validación (400) → actividad (404) → capacidad (400 `Capacity exceeded. Available: N,
  Requested: M`) → cobro (402) → 201 con la `Booking` sin `activity`.
- No comprueba estado ni fecha de la actividad. El importe es `price × participants` y no se
  devuelve.

El comportamiento exigido está en `specs/activity-booking/spec.md`.

## Goals / Non-Goals

**Goals:**
- Un comando fino que reutiliza la sesión, el cliente autorizado y el detalle de actividad.
- Comprobaciones de reservabilidad puras y fáciles de probar, separadas del comando.

**Non-Goals:**
- Comprobar en el cliente la capacidad (con `maxParticipants`) o `minParticipants`: decide el
  servidor.
- Reintentar la reserva o deshacer el cobro.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py              # + Booking, parse_booking(), create_booking()
  booking_rules.py           # check_bookable(activity, now) -> None
  commands/bookings_cmd.py   # grupo `bookings`, subcomando `create`
  cli.py                     # registra el grupo `bookings`
tests/
  test_api_client.py  test_booking_rules.py  test_bookings_cmd.py
```

`booking_rules.py` no hace HTTP ni imprime: recibe el `Activity` y la hora actual y lanza
`ActivityBookingsError`. *Alternativa descartada:* meter la regla en el comando; habría que
probarla siempre a través de la CLI y respx.

### Cliente de API

- `Booking`: dataclass frozen con `id`, `activity_id`, `user_id`, `participants: int`,
  `created_at` y `payment_status`.
- `parse_booking(data: object) -> Booking`: validación manual, igual que `parse_activity()`.
  `participants` acepta `int` (no `bool`) o `float` con valor entero. Si falta `paymentStatus`, se
  usa `pending`, como hace el servidor en `GET /bookings`. Cualquier otro campo ausente o con tipo
  incorrecto → `ApiResponseError("invalid response from the API: booking has no valid '<campo>'")`.
- `create_booking(activity_id: str, participants: int) -> Booking`: `_request("POST", "/bookings",
  json={"activityId": activity_id, "participants": participants})`. `participants` es `int` en
  Python, así que se serializa como número entero.
- Los errores 400, 402 y 404 llegan como `ApiError` con el mensaje de la API por la ruta genérica
  de `_request()`; no hace falta traducción específica.

### Regla de reservabilidad

`check_bookable(activity: Activity, now: datetime) -> None`:

1. `status != "published"` → `ActivityBookingsError(f"activity {id} is not open for booking
   (status: {status})")`.
2. Fecha:
   - Si `date.fromisoformat()` la acepta (solo fecha), es pasada si `fecha < now.date()` (UTC). Así
     la actividad de hoy sigue siendo reservable todo el día.
   - Si no, `datetime.fromisoformat()`; si no tiene zona, se asume UTC. Es pasada si `<= now`.
   - Si ninguna la acepta → `ActivityBookingsError(f"cannot read the date of activity {id}:
     {date!r}")`.
   - Pasada → `ActivityBookingsError(f"activity {id} already took place on {_format_date(date)}")`.

El estado se comprueba primero porque es el motivo más claro para el usuario. `now` se obtiene en
el comando con una función pequeña `_now()` que los tests pueden parchear (como en `whoami` y
`require_session()`), necesaria solo para el escenario «Actividad de hoy sin hora».

*Alternativa descartada:* comprobar solo el estado. La API deja reservar actividades ya pasadas
(Reglas 3) y los datos de ejemplo tienen una `published` con fecha pasada (`activity-3`).

### Comando `bookings create`

```python
create(ctx, activity_id: Annotated[str, typer.Argument(...)],
       participants: Annotated[int, typer.Option("--participants", "-p", min=1)] = 1,
       yes: Annotated[bool, typer.Option("--yes", "-y")] = False)
```

Orden: Typer (argumento obligatorio, `min=1`, entero; código 2) → `activity_id.strip()` vacío →
`typer.BadParameter("ACTIVITY_ID cannot be empty", param_hint="ACTIVITY_ID")` (código 2) →
`load_settings(ctx.obj)` → `authorized_client(settings)` → `get_activity()` →
`check_bookable(detail.activity, _now())` → confirmación si no hay `--yes` → `create_booking()`
dentro de `login_hint()` → salida. Usa `handle_errors`.

- La sesión se comprueba antes del `GET`, aunque sea una ruta pública: sin sesión no tiene sentido
  consultar la actividad ni pedir confirmación.
- El `GET` lleva la cabecera `Authorization` porque usa el cliente autorizado. Es inocuo (la ruta
  es pública) y evita crear dos clientes. `login_hint()` envuelve también el `GET` por coherencia.
- Total: `activity.price * participants`, formateado con `_format_price()`.
- Confirmación: `typer.confirm(f"Book {n} seat(s) for {name} ({id}) on {fecha} for a total of
  {total}?", default=False)`. Si se rechaza: `Booking cancelled.` y código 0.
- Salida: `Booking <id> created.` y una tabla Rich sin cabecera, como en `activities show`, con
  las filas ID, Activity (`<name> (<id>)`), Date, Participants, Total y Payment.
- Nombre `create` por coherencia con `activities create`, y para dejar sitio a `bookings list` y
  `bookings show` en el change de consulta.

Ejemplos:

```console
$ activity-bookings bookings create activity-2 -p 2
Book 2 seat(s) for City Bike Tour (activity-2) on 2026-12-20 for a total of 70.00? [y/N]: y
Booking booking-1 created.
ID            booking-1
Activity      City Bike Tour (activity-2)
Date          2026-12-20
Participants  2
Total         70.00
Payment       paid

$ activity-bookings bookings create activity-2
Book 1 seat(s) for City Bike Tour (activity-2) on 2026-12-20 for a total of 35.00? [y/N]: n
Booking cancelled.

$ activity-bookings bookings create activity-4 --yes
Error: activity activity-4 is not open for booking (status: draft)

$ activity-bookings bookings create activity-3 --yes
Error: activity activity-3 already took place on 2026-08-25 14:00 UTC

$ activity-bookings bookings create activity-2 -p 20 --yes
Error: Capacity exceeded. Available: 13, Requested: 20

$ activity-bookings bookings create activity-2 --participants 0
Usage: activity-bookings bookings create [OPTIONS] ACTIVITY_ID
Error: Invalid value for '--participants' / '-p': 0 is not in the range x>=1.

$ activity-bookings bookings create activity-2
Error: not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `parse_booking` (completa, sin `paymentStatus`, `participants`
  `2.0`, `participants` booleano o cadena, campo ausente, no es un objeto) y `create_booking` con
  respx (ruta, cuerpo JSON con `participants` entero, cabecera con token, 201, 400, 402, 404, 500).
- `tests/test_booking_rules.py`: `check_bookable` con cada estado no `published`, fecha pasada y
  futura con hora, fecha sin hora de ayer, hoy y mañana, fecha con hora sin zona y fecha ilegible.
  Se pasa `now` fijo, sin parchear.
- `tests/test_bookings_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`,
  reutilizando el fixture de sesión válida y el helper de JWT de `add-activity-management` y el
  helper de actividad JSON de `add-activity-list`/`add-activity-detail`. Las fechas de los datos
  son de 2000 o 2100, para no depender del reloj; solo el escenario «hoy» parchea `_now()`. La
  confirmación se prueba con `input="y\n"` o `"n\n"`. Para «sin petición `POST /bookings`», se
  comprueba que la ruta respx de `POST /bookings` no tiene llamadas.

## Risks / Trade-offs

- [Dos peticiones por reserva (`GET` y `POST`), y la actividad puede cambiar entre ambas] → El
  servidor sigue siendo la autoridad para la capacidad y la existencia. Un cambio de estado en ese
  intervalo no se detecta, pero es improbable en una herramienta de formación.
- [El total mostrado lo calcula la CLI; la API no devuelve el importe] → Usa la misma fórmula que
  el servidor (Reglas 5). Si el precio cambia entre el `GET` y el `POST`, el total puede no
  coincidir. Se acepta.
- [Con el fallo de login del servidor (Discrepancias 1a), el usuario trabajará con la sesión de
  `auth register`] → Funciona igual: las reservas no exigen ser dueño de la actividad.
- [El 402 no se puede provocar con los datos de ejemplo (importe múltiplo de 1000)] → Se prueba con
  respx. El README lo menciona.
- [Una fecha sin hora se interpreta en UTC, no en la zona del usuario] → Coherente con
  `_format_date()` y con el servidor. Se documenta en el README.
- [Depende de cinco changes pendientes] → La tarea 1.1 lo comprueba. Hay que archivarlos antes, para
  que `auth-session` y `activity-browsing` existan en `openspec/specs/`.
