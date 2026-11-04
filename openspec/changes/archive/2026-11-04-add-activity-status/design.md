# Design

## Context

Este change supone implementado `add-activity-management` (y los changes de los que depende).
Reutiliza:

- `api_client.py`: `ApiClient(..., token=...)` y `_request()`, con su traducción de errores (4xx con
  JSON → `<message>`; 5xx → `API error <status>: <message>`; sin JSON válido → mensaje genérico con
  el código HTTP); `parse_activity()` y `_activity_path()` (`quote(id, safe="")`).
- `commands/_auth.py`: `authorized_client(settings)` y `login_hint()`.
- `commands/activities_cmd.py`: el enum `ActivityStatus` (los seis estados, hoy usado por
  `list --status`), `_print_activity(activity, done)` y el patrón de confirmación de
  `activities delete` (sesión comprobada antes de preguntar, `typer.confirm(..., default=False)`).

Contrato (`docs/api-reference.md`, `PATCH /activities/:id/status`, actualizado con el informe del
`api-explorer`):

- Protegido. Cuerpo `{"status": "<estado>"}`; 200 con la `Activity` completa sin envolver.
- Orden de errores: 401 → 400 de cuerpo o estado desconocido → 404 → 403 → 400 de transición
  (`Invalid status transition from <a> to <b>. Valid transitions are: <lista | none (terminal
  state)>`) → 500 `Failed to transition activity status`. Todos con `errors: []`.
- Sin efectos secundarios sobre reservas o pagos.

El comportamiento exigido está en `specs/activity-management/spec.md`.

## Goals / Non-Goals

**Goals:**
- Un subcomando fino que reutiliza el cliente autorizado, el modelo `Activity` y la ficha de
  `create`/`update`.
- No cambiar el comportamiento de `list`, `show`, `create`, `update` ni `delete`.

**Non-Goals:**
- Pedir `GET /activities/:id` antes del `PATCH` (para validar la transición o mostrar el estado
  anterior).
- Una regla de transiciones en el cliente (como `booking_rules.py`).

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py                # + ApiClient.change_activity_status()
  commands/activities_cmd.py   # + subcomando `status`, FINAL_STATUSES
tests/
  test_api_client.py  test_activities_cmd.py
```

### Cliente de API

`ApiClient.change_activity_status(activity_id: str, status: str) -> Activity`:
`_request("PATCH", f"{_activity_path(activity_id)}/status", json={"status": status})` y
`parse_activity()`. Los errores llegan como `ApiError` por la ruta genérica de `_request()`; no hace
falta traducción específica.

Recibe `str` y no `ActivityStatus` para que la capa de API no dependa del módulo de comandos, donde
vive el enum. *Alternativa descartada:* mover `ActivityStatus` a `api_client.py`; afecta a
`list --status` sin aportar nada a este change.

### Comando `activities status`

```python
@app.command("status")
@handle_errors
def change_status(
    ctx: typer.Context,
    activity_id: Annotated[str, typer.Argument(metavar="ACTIVITY_ID", help="ID of the activity.")],
    new_status: Annotated[ActivityStatus, typer.Argument(metavar="NEW_STATUS", help=...)],
    yes: Annotated[bool, typer.Option("--yes", "-y", help=...)] = False,
) -> None:
```

Orden:

1. Typer exige los dos argumentos y valida `NEW_STATUS` contra `ActivityStatus` (código 2). Su
   mensaje ya nombra `NEW_STATUS` y los valores válidos, comprobado:
   `Invalid value for 'NEW_STATUS': 'open' is not one of 'draft', 'published', ...` y
   `Missing argument 'NEW_STATUS'. Choose from: ...`.
2. `activity_id.strip()` vacío → `typer.BadParameter("ACTIVITY_ID cannot be empty",
   param_hint="ACTIVITY_ID")` (código 2).
3. `load_settings(ctx.obj)` → `authorized_client(settings)` (falla sin sesión antes de preguntar).
4. Si `new_status in FINAL_STATUSES` y no `--yes`: `typer.confirm(f"Change activity {id} to
   {status}? This cannot be undone.", default=False)`; si no → `Status change cancelled.` y salir con
   código 0.
5. `change_activity_status()` dentro de `login_hint()` → `_print_activity(activity, f"is now
   {activity.status}")`.

`FINAL_STATUSES = frozenset({ActivityStatus.DONE, ActivityStatus.CANCELLED})`, en
`activities_cmd.py`. El estado mostrado es el que devuelve la API, no el pedido.

*Alternativas descartadas:*
- Validar la transición en el cliente: duplicaría la máquina de estados del servidor y obligaría a
  un `GET` previo; el mensaje del 400 ya dice qué transiciones son válidas.
- Confirmar siempre: las transiciones no finales se pueden encadenar o corregir, y la API rechaza las
  inválidas.

### Presentación

Igual que `create` y `update`: una línea de resultado y la ficha sin cabecera de `_print_activity`.

```console
$ activity-bookings activities status activity-5 published
Activity activity-5 is now published.
ID        activity-5
Name      Yoga
Date      2027-01-15
Location  Park
Price     20.00
Capacity  10
Status    published

$ activity-bookings activities status activity-5 cancelled
Change activity activity-5 to cancelled? This cannot be undone. [y/N]: n
Status change cancelled.

$ activity-bookings activities status activity-5 done --yes
Error: Invalid status transition from published to done. Valid transitions are: confirmed, cancelled, sold-out

$ activity-bookings activities status activity-2 published
Error: You can only transition your own activities

$ activity-bookings activities status activity-5 open
Usage: activity-bookings activities status [OPTIONS] {ACTIVITY_ID} {NEW_STATUS}
Error: Invalid value for 'NEW_STATUS': 'open' is not one of 'draft', 'published', 'confirmed',
'sold-out', 'done', 'cancelled'.
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `change_activity_status` con respx (método, ruta, ID `a/b` como
  `a%2Fb`, cuerpo, cabecera con token, 200 parseado como `Activity`, y 400, 403, 404 y 500 como
  `ApiError` con su `status_code`; 200 incompleto como `ApiResponseError`).
- `tests/test_activities_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`,
  reutilizando los helpers de sesión, JWT y actividad JSON existentes. Confirmación con `input=`.
  «Sin petición HTTP» con `respx_mock.calls` vacío. El test de la ayuda del grupo se amplía con
  `status`.

## Risks / Trade-offs

- [Cancelar una actividad no cancela ni reembolsa sus reservas] → Es comportamiento del servidor; la
  CLI no lo oculta ni lo compensa. Se documenta en el README.
- [El login no funciona con los usuarios de ejemplo (Discrepancias 1)] → Solo se pueden cambiar las
  actividades creadas con la sesión de `auth register`; las de ejemplo darán 403. Se documenta.
- [Un estado se pide en minúsculas exactas] → Typer distingue mayúsculas igual que la API; el error
  lista los valores válidos.
- [Ediciones concurrentes de `activities_cmd.py` con otros changes] → Cambio aditivo; no se toca
  ningún subcomando existente.
