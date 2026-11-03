# Design

## Context

Este change se apoya en `add-user-registration` y supone que ya está implementado. De él reutiliza:

- `api_client.py`: `ApiClient(base_url, timeout)` sobre `httpx.Client` y `_request()`, que
  centraliza la traducción de errores de red y HTTP (tabla de errores de su `design.md`).
- `errors.py`: `ApiError`, `ApiConnectionError` y `ApiResponseError`, y `handle_errors`.

No necesita nada de `add-user-login` ni de la sesión: `GET /activities` es público.

Contrato de la API (`docs/api-reference.md`, Actividades):

- `GET /activities` responde 200 con un array JSON de `Activity` sin envoltorio y sin paginación.
- Query: `q` (subcadena sin distinguir mayúsculas en `name`, `location` y `slug`), `_sort` y
  `_order`. `_order` se ignora si no hay `q`, `slug` ni `_sort`. **No hay filtro por `status`.**
- `date` puede ser solo fecha (`2026-10-26`) o fecha y hora UTC (`2026-08-25T14:00:00.000Z`).
- `price` es un número (por plaza); `updatedAt` es opcional.
- Único error documentado: 500 `{"message":"Failed to retrieve activities","errors":[]}`.

El comportamiento exigido está en `specs/activity-browsing/spec.md`.

## Goals / Non-Goals

**Goals:**
- Un modelo `Activity` y un método de cliente que el futuro `activities show` y los comandos de
  reservas puedan reutilizar.
- Un comando fino: valida opciones, llama al cliente, filtra por estado e imprime.

**Non-Goals:**
- Cachear el listado o reintentar peticiones.
- Modelar todos los campos de `Activity` (solo los que se muestran; ver Decisiones).

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py               # + Activity, ActivityStatus (Literal), list_activities()
  commands/activities_cmd.py  # grupo `activities` con `list`
  cli.py                      # app.add_typer(activities_cmd.app, name="activities")
tests/
  test_api_client.py          # + tests de Activity y list_activities
  test_activities_cmd.py
```

### Modelo `Activity`

Dataclass frozen con `id: str`, `name: str`, `date: str`, `location: str`, `price: float`,
`max_participants: int` y `status: str`. Un `parse_activity(data: object) -> Activity` valida
tipos a mano, igual que el parseo de `User` en el registro (sin pydantic), y lanza
`ApiResponseError("invalid response from the API: activity <id o posición> has no valid
'<campo>'")`. `price` acepta `int` o `float` pero no `bool`. Los campos extra se ignoran.

- `status` se guarda como `str` y no se valida contra los seis estados: si el servidor añade uno,
  la CLI lo muestra en vez de fallar.
- `date` se guarda tal cual (cadena); el formateo es cosa de la presentación.
- *Alternativa descartada:* modelar todos los campos (`slug`, `duration`, `minParticipants`,
  `userId`, `createdAt`, `updatedAt`). YAGNI: se añadirán cuando el detalle los muestre.

### Cliente de API

`ApiClient.list_activities(search: str | None = None, sort: str | None = None, order: str =
"asc") -> list[Activity]`:

- Construye los parámetros: `q` si hay `search`; `_sort` y `_order` solo si hay `sort`. Así nunca
  se envía un `_order` que el servidor ignoraría.
- Llama a `_request("GET", "/activities", params=...)`. Si `_request()` del registro no acepta
  `params`, se le añade ese argumento opcional (sin cambiar su comportamiento para `POST`).
- Si el JSON no es una lista lanza `ApiResponseError("invalid response from the API: expected a
  list of activities")`; si lo es, parsea cada elemento con `parse_activity`.
- No envía `Authorization`: el cliente del registro no añade token por defecto.

### Comando `activities list`

Opciones (Typer):

| Opción | Tipo | Validación |
|---|---|---|
| `--search TEXT` | `str \| None` | vacía o en blanco → `typer.BadParameter` (código 2) |
| `--sort` | `SortField` (`StrEnum`: date, price, name, location) | Typer rechaza otros valores (código 2) |
| `--order` | `SortOrder` (`StrEnum`: asc, desc), por defecto `None` | sin `--sort` → `typer.BadParameter` (código 2) |
| `--status` | `ActivityStatus` (`StrEnum` con los seis estados) | Typer rechaza otros valores (código 2) |

`--order` tiene `None` por defecto (no `asc`) para poder detectar que se ha pasado sin `--sort`;
el comando usa `asc` si no se indica. Los errores de uso se validan antes de cargar la
configuración y de llamar a la API.

Orden de pasos: validar opciones → `load_settings(ctx.obj)` → `ApiClient(settings.api_url)
.list_activities(...)` → filtrar por `status` en el cliente (manteniendo el orden) → imprimir. El
comando usa `handle_errors`, así que los errores de API y de configuración salen como
`Error: ...` con código 1.

Presentación (funciones pequeñas en el módulo del comando):

- `_format_date(value)`: si `date.fromisoformat` la acepta (solo fecha) se muestra tal cual; si
  `datetime.fromisoformat` la acepta, se convierte a UTC y se muestra `YYYY-MM-DD HH:MM UTC`; si
  no, se muestra la cadena original. Python 3.12 acepta el sufijo `Z`.
- `_format_price(value)`: dos decimales (`35.00`), sin símbolo de moneda porque la API no indica
  ninguna.
- Tabla Rich con título `Activities` y columnas ID, Name, Date, Location, Price (alineada a la
  derecha), Capacity (derecha) y Status, seguida de `N activities` (`1 activity` en singular).
- Sin resultados: `No activities found.` y código 0.

*Alternativa descartada:* filtrar por defecto solo las `published` y futuras. El usuario eligió
mostrar todas; el filtro queda en `--status`.

Ejemplos (los lugares de las actividades distintas de `activity-2` son ilustrativos):

```console
$ activity-bookings activities list
                                  Activities
 ID          Name                               Date                  Location      Price  Capacity  Status
 activity-1  Surf                               2026-10-26            Beach        158.00         8  draft
 activity-2  City Bike Tour                     2026-12-20            City Center   35.00        15  published
 activity-3  Cooking Workshop: Italian Cuisine  2026-08-25 14:00 UTC  Food Lab      75.00        12  published
 activity-4  Photography Walk                   2027-03-01 09:00 UTC  Old Town      30.00        10  draft
4 activities

$ activity-bookings activities list --status published --sort price --order desc
 ...
 activity-3  Cooking Workshop: Italian Cuisine  2026-08-25 14:00 UTC  Food Lab      75.00        12  published
 activity-2  City Bike Tour                     2026-12-20            City Center   35.00        15  published
2 activities

$ activity-bookings activities list --search zzz
No activities found.

$ activity-bookings activities list --order desc
Usage: activity-bookings activities list [OPTIONS]
Error: Invalid value for '--order': --order requires --sort

$ activity-bookings activities list
Error: cannot connect to the API at http://localhost:3000
```

### Dependencias

Ninguna nueva: Typer, Rich, httpx y respx ya forman parte del stack (las dos últimas las añade
`add-user-registration`).

### Tests

- `tests/test_api_client.py`: `parse_activity` (válida, `price` entero y decimal, campo ausente,
  `price` booleano) y `list_activities` con respx (parámetros enviados, sin `_order` sin `sort`,
  respuesta no lista, elemento inválido, 500).
- `tests/test_activities_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`.
  Para "sin petición HTTP" se usa `respx_mock` sin rutas y se comprueba `respx_mock.calls` vacío;
  para la ausencia de `Authorization`, `route.calls.last.request.headers`.
- Un helper de test construye actividades JSON con valores por defecto para no repetir los campos.

Los escenarios de 401/403 de las reglas del proyecto no aplican: la ruta es pública. En su lugar,
la spec exige que no se envíen credenciales y cubre el 404 de un servidor equivocado.

## Risks / Trade-offs

- [`q` repetido en la query daría 500 en el servidor (Discrepancias 9)] → la CLI solo envía un `q`.
- [Una actividad con datos inválidos hace fallar todo el listado] → se prefiere un error claro que
  mostrar datos a medias; el mensaje indica qué actividad y qué campo.
- [Sin paginación, un catálogo grande produce una tabla larga] → aceptable en un sistema de
  formación con pocos datos.
- [La columna Capacity muestra la capacidad total, no las plazas libres] → la API no expone las
  libres; la cabecera dice "Capacity" para no inducir a error.
- [Depende de `add-user-registration`] → la tarea 1.1 lo comprueba antes de empezar.
