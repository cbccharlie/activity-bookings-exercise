# Design

## Context

Este change supone implementados tres changes pendientes y reutiliza sus piezas:

- `add-user-registration`: `ApiClient(base_url, timeout)` con `_request()` y la tabla de traducción
  de errores (`ApiError` con `status_code` y `field_errors`, `ApiConnectionError`,
  `ApiResponseError`); `Session(api_url, access_token, user)` y `SessionError`.
- `add-user-login`: `load_session()` (con su `SessionError` que ya incluye la ruta y la sugerencia
  de `auth login`) y `token_expiry(token) -> datetime | None`. Su `design.md` dejó pendiente para
  este change comprobar que la `api_url` de la sesión coincide con la configuración.
- `add-activity-list`: grupo `activities` en `commands/activities_cmd.py`, modelo frozen `Activity`
  (`id`, `name`, `date`, `location`, `price`, `max_participants`, `status`), `parse_activity()`,
  `_format_date()` y `_format_price()`.

Contrato (`docs/api-reference.md`, Actividades):

- `POST /activities`: 201 con la `Activity`; `status` por defecto `draft`, `duration` por defecto
  60; `date` válida y futura; números o cadenas numéricas.
- `PUT /activities/:id`: campos opcionales, números como `number`; enviar `status` da 400; 404
  antes que 403; 200 con la `Activity`.
- `DELETE /activities/:id`: 204 sin cuerpo; 403, 404 o 500.
- Rutas protegidas: 401 con `errors: []` sin token o con token inválido o caducado.

El comportamiento exigido está en `specs/activity-management` y `specs/auth-session`.

## Goals / Non-Goals

**Goals:**
- Un mecanismo de rutas protegidas (comprobar la sesión, enviar el token, traducir el 401) que los
  comandos de reservas reutilicen sin cambios.
- Comandos finos que reutilizan el modelo y el formateo del listado.

**Non-Goals:**
- Validar en el cliente las reglas del servidor (fecha futura, precio positivo, mínimo ≤ máximo):
  se delega en el 400 de la API para no duplicar reglas que pueden cambiar.
- Leer la actividad antes de borrarla para mostrar su nombre en la confirmación.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py               # + token en ApiClient, NewActivity, ActivityChanges,
                              #   create_activity, update_activity, delete_activity
  session.py                  # + require_session(api_url)
  commands/_auth.py           # authorized_client(settings), login_hint()
  commands/activities_cmd.py  # + create, update, delete
tests/
  test_api_client.py  test_session.py  test_activities_cmd.py
```

### Cliente de API

- `ApiClient(base_url, timeout=10.0, token: str | None = None)`. Con `token`, el `httpx.Client` se
  crea con la cabecera `Authorization: Bearer <token>`. Sin él, no se envía nada (el listado y el
  registro siguen igual).
  - *Alternativa descartada:* un parámetro `token` en cada método; repite la cabecera y permite
    olvidarla.
- Datos de entrada como dataclasses frozen con `to_json() -> dict[str, object]`:
  - `NewActivity(name, price: float, date, location, min_participants: int, max_participants: int,
    duration: int | None = None)`. Omite `duration` si es `None`.
  - `ActivityChanges(...)`: los mismos campos, todos `| None = None`, y `is_empty()`. `to_json()`
    omite los `None`.
  - Las claves se traducen a camelCase (`minParticipants`, `maxParticipants`). No existe `status`
    en ninguno de los dos, así que no se puede enviar.
- `create_activity(NewActivity) -> Activity` (`POST /activities`) y
  `update_activity(activity_id, ActivityChanges) -> Activity` (`PUT /activities/<id>`) parsean la
  respuesta con `parse_activity()`.
- `delete_activity(activity_id) -> None` (`DELETE /activities/<id>`). Si `_request()` del registro
  siempre parsea JSON, se le añade un modo sin cuerpo para el 204, sin cambiar el resto.
- El ID se codifica con `urllib.parse.quote(activity_id, safe="")` para que un `/` no cambie la
  ruta.
- Typer convierte `--price 20` en `20.0`, que se serializa como `20.0`. Para el servidor es el
  mismo número y los tests comparan el JSON parseado (`20.0 == 20`).

### Sesión en rutas protegidas

`require_session(api_url: str) -> Session` en `session.py` (sin HTTP):

1. `load_session()`. Si devuelve `None`: `SessionError("not logged in; run 'activity-bookings auth
   login' or 'activity-bookings auth register'")`. Si el fichero no es válido, se propaga su
   `SessionError`.
2. Si `session.api_url.rstrip("/") != api_url.rstrip("/")`: `SessionError("the session belongs to
   <session url>, but the configured API is <api_url>; run 'activity-bookings auth login'")`.
3. Si `token_expiry()` devuelve una fecha anterior a `_now()`: `SessionError("your session expired
   on <fecha> UTC; run 'activity-bookings auth login'")`. Si devuelve `None`, se continúa: el
   servidor decide. `_now()` es una función pequeña que se puede parchear, igual que en `whoami`.

En `commands/_auth.py`:

- `authorized_client(settings) -> ApiClient`: `require_session(settings.api_url)` y
  `ApiClient(settings.api_url, token=session.access_token)`.
- `login_hint()`: context manager que convierte un `ApiError` con `status_code == 401` en
  `ActivityBookingsError(f"{exc}\nRun 'activity-bookings auth login' to start a new session.")`.
  La sesión no se borra: el usuario decide si hace login de nuevo.
- *Alternativa descartada:* añadir la sugerencia en `ApiClient`; mezclaría textos de la CLI en la
  capa HTTP.

### Comandos

Orden común: validación de Typer (código 2) → validación propia de uso → `load_settings(ctx.obj)`
→ `authorized_client()` → (solo `delete`) confirmación → llamada dentro de `login_hint()` → salida.
Así la sesión se comprueba antes de pedir confirmación y nunca hay petición si falla algo previo.
Todos usan `handle_errors`.

| Comando | Argumentos y opciones |
|---|---|
| `create` | `--name`, `--price FLOAT`, `--date`, `--location`, `--min-participants INT`, `--max-participants INT` obligatorias; `--duration INT` (minutos) opcional |
| `update ACTIVITY_ID` | las mismas opciones, todas opcionales; sin ninguna → `typer.BadParameter("at least one field to update is required", param_hint="options")` (código 2) |
| `delete ACTIVITY_ID` | `--yes` / `-y`; si no, `typer.confirm(f"Delete activity {id}?", default=False)` |

- `--date` se envía tal cual. La ayuda indica `YYYY-MM-DD` o ISO 8601 con hora y zona (p. ej.
  `2027-01-15T10:00:00Z`); el servidor la valida.
- Salida de `create` y `update`: una línea `Activity <id> created.` / `updated.` y una tabla Rich
  sin cabecera, como `config` y `whoami`, con las filas ID, Name, Date, Location, Price, Capacity y
  Status, formateadas con `_format_date()` y `_format_price()`.
- `delete`: `Activity <id> deleted.`; si no se confirma, `Deletion cancelled.` con código 0.

Ejemplos:

```console
$ activity-bookings activities create --name Yoga --price 20 --date 2027-01-15 \
    --location Park --min-participants 2 --max-participants 10
Activity activity-5 created.
ID        activity-5
Name      Yoga
Date      2027-01-15
Location  Park
Price     20.00
Capacity  10
Status    draft

$ activity-bookings activities update activity-5 --price 25
Activity activity-5 updated.
...
Price     25.00
...

$ activity-bookings activities update activity-5
Usage: activity-bookings activities update [OPTIONS] ACTIVITY_ID
Error: Invalid value for options: at least one field to update is required

$ activity-bookings activities delete activity-5
Delete activity activity-5? [y/N]: n
Deletion cancelled.

$ activity-bookings activities delete activity-2 --yes
Error: You can only delete your own activities

$ activity-bookings activities create --name Yoga --price 0 --date 2020-01-01 \
    --location Park --min-participants 2 --max-participants 10
Error: Validation failed
  - date: Date must be in the future
  - price: Price must be greater than 0

$ activity-bookings activities create ...
Error: your session expired on 2026-11-02 10:15 UTC; run 'activity-bookings auth login'

$ activity-bookings activities update activity-5 --price 25
Error: Invalid or expired token. Please login again.
Run 'activity-bookings auth login' to start a new session.
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `to_json()` de `NewActivity` y `ActivityChanges`, cabecera con y sin
  token, los tres métodos con respx (ruta, cuerpo, 201/200/204, 400, 403, 404, 500, respuesta
  incompleta) e ID con `/` codificado.
- `tests/test_session.py`: `require_session()` sin sesión, con otra `api_url`, con la barra final
  como única diferencia, con `exp` en 2000 y en 2100, y con un token que no es JWT.
- `tests/test_activities_cmd.py`: un test por escenario de las specs. Un fixture escribe una sesión
  válida con `save_session()` y un JWT con `exp` en 2100 (helper de `add-user-login`). Para "sin
  petición HTTP", `respx_mock` sin rutas y `respx_mock.calls` vacío.

## Risks / Trade-offs

- [Fallo del servidor: `nextId` empieza en 1 y `POST /activities` podría sobrescribir `activity-1`
  (Discrepancias 1b)] → No se puede corregir desde el cliente. Se documenta en el README.
- [El login puede fallar con los usuarios existentes (Discrepancias 1a)] → Se trabaja con la sesión
  de `auth register`; ese usuario no es dueño de las actividades de la semilla, que darán 403. Se
  documenta.
- [Borrar una actividad con reservas deja `GET /bookings` respondiendo 500 (Discrepancias 7)] → La
  CLI no puede saberlo sin ver todas las reservas. Se documenta en el README.
- [La comprobación local de `exp` no verifica la firma] → Solo evita una petición inútil; si no se
  puede leer, decide el servidor.
- [Una fecha sin zona con hora la interpreta el servidor en su zona horaria] → La ayuda recomienda
  indicar la zona.
- [Depende de tres changes pendientes] → La tarea 1.1 lo comprueba. Hay que archivarlos antes que
  este, para que `auth-session` y `activity-browsing` existan en `openspec/specs/`.
