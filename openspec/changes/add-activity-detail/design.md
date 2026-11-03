# Design

## Context

Este change supone implementados `add-user-registration` y `add-activity-list`. De ellos reutiliza:

- `api_client.py`: `ApiClient(base_url, timeout)` y `_request()`, que traduce los errores de red y
  HTTP (4xx con JSON → `<message>`; 5xx con JSON → `API error <status>: <message>`; sin JSON válido
  → `API returned HTTP <status> with an unexpected response`). También el modelo frozen `Activity`
  (`id`, `name`, `date`, `location`, `price`, `max_participants`, `status`) y `parse_activity()`.
- `commands/activities_cmd.py`: el grupo `activities`, `_format_date()` y `_format_price()`.
- `errors.py`: `ApiError`, `ApiConnectionError`, `ApiResponseError` y `handle_errors`.

Contrato de la API (`docs/api-reference.md`, `GET /activities/:id`):

- Público. 200 con un objeto `Activity` sin envoltorio, con la misma forma que en el listado:
  `id`, `name`, `slug`, `price`, `date`, `duration`, `location`, `minParticipants`,
  `maxParticipants`, `status`, `userId`, `createdAt` y, opcional, `updatedAt`.
- 404 `{"message":"Activity not found","errors":[]}` y 500
  `{"message":"Failed to retrieve activity","errors":[]}`.
- No informa de plazas ocupadas ni libres.

El comportamiento exigido está en `specs/activity-browsing/spec.md`.

## Goals / Non-Goals

**Goals:**
- Reutilizar `Activity` y su parseo sin cambiar el comportamiento de `activities list`.
- Un comando fino: valida el ID, llama al cliente e imprime la ficha.

**Non-Goals:**
- Calcular plazas libres combinando reservas (la CLI solo ve las propias).
- Cachear actividades ni reutilizar el listado para obtener el detalle.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py               # + ActivityDetail, parse_activity_detail(), get_activity()
  commands/activities_cmd.py  # + subcomando `show`, _format_duration(), _detail_table()
tests/
  test_api_client.py          # + tests de ActivityDetail y get_activity
  test_activities_cmd.py      # + tests de `activities show`
```

### Modelo `ActivityDetail`

Dataclass frozen que **compone** el `Activity` existente y añade los campos del detalle:
`activity: Activity`, `slug: str`, `duration: int`, `min_participants: int`, `user_id: str`,
`created_at: str` y `updated_at: str | None`.

`parse_activity_detail(data: object) -> ActivityDetail` llama primero a `parse_activity(data)` y
después valida a mano los campos nuevos, con el mismo estilo de error: `ApiResponseError("invalid
response from the API: activity <id> has no valid '<campo>'")`. Reglas:

- `slug`, `userId` y `createdAt`: cadenas.
- `duration` y `minParticipants`: `int`, no `bool`. Un `float` con valor entero (`120.0`) se
  acepta y se convierte a `int`, porque el servidor admite cadenas numéricas al crear.
- `updatedAt`: ausente o `null` → `None`; si existe, debe ser cadena.
- Si `data` no es un objeto JSON: `invalid response from the API: expected an activity`.

*Alternativas descartadas:*
- Añadir los campos nuevos a `Activity`. Obligaría a que el listado (y `create`/`update` de
  `add-activity-management`) exigiera campos que no muestra, y un fallo en uno de ellos rompería
  `activities list`.
- Hacerlos opcionales en `Activity`. Esconde datos ausentes y llena los consumidores de `None`.

### Cliente de API

`ApiClient.get_activity(activity_id: str) -> ActivityDetail`:

- Llama a `_request("GET", f"/activities/{quote(activity_id, safe='')}")`, con el mismo criterio de
  codificación que `add-activity-management`, para que `/` o espacios no cambien la ruta.
- Parsea con `parse_activity_detail()`. No envía `Authorization`.
- El 404 con JSON llega como `ApiError("Activity not found")` gracias a `_request()`: no hace falta
  traducción específica.

### Comando `activities show`

`show(ctx, activity_id: Annotated[str, typer.Argument(help="ID of the activity, e.g. activity-2.")])`.

Orden: Typer exige el argumento (código 2) → si `activity_id.strip()` está vacío,
`typer.BadParameter("ACTIVITY_ID cannot be empty", param_hint="ACTIVITY_ID")` (código 2) →
`load_settings(ctx.obj)` → `ApiClient(settings.api_url).get_activity(activity_id.strip())` →
imprimir. Usa `handle_errors`.

Presentación: tabla Rich sin cabecera (`show_header=False`, `box=None`), como `config`, con la
etiqueta en negrita y el valor con `markup=False`/`highlight=False` donde aplique:

| Fila | Valor |
|---|---|
| ID, Name, Slug, Location, Status | tal cual |
| Date, Created, Updated | `_format_date()` del listado |
| Duration | `_format_duration(minutes)` → `120 min` |
| Price | `_format_price()` → `35.00` |
| Min participants, Capacity | entero |
| Organizer | `userId` tal cual |

`Updated` solo se añade si `updated_at` no es `None`. Capacity mantiene el nombre del listado
(capacidad total, no plazas libres).

*Alternativa descartada:* un panel Rich con texto libre. La tabla de pares es más fácil de leer y
de comprobar en los tests, y es coherente con `config` y con la salida de `create`/`update`.

Ejemplos:

```console
$ activity-bookings activities show activity-2
ID                activity-2
Name              City Bike Tour
Slug              city-bike-tour
Date              2026-12-20
Duration          120 min
Location          City Center
Price             35.00
Min participants  3
Capacity          15
Status            published
Organizer         user-1
Created           2026-01-16 10:00 UTC

$ activity-bookings activities show activity-99
Error: Activity not found

$ activity-bookings activities show " "
Usage: activity-bookings activities show [OPTIONS] ACTIVITY_ID
Error: Invalid value for ACTIVITY_ID: ACTIVITY_ID cannot be empty

$ activity-bookings activities show activity-2
Error: cannot connect to the API at http://localhost:3000
```

### Dependencias

Ninguna nueva.

### Tests

- `tests/test_api_client.py`: `parse_activity_detail` (completa, sin `updatedAt`, `updatedAt`
  `null`, `duration` `120.0`, `duration` ausente o booleano, `userId` no cadena, objeto que no es
  dict) y `get_activity` con respx (ruta, ID codificado, sin `Authorization`, 404, 500).
- `tests/test_activities_cmd.py`: un test por escenario de la spec con `CliRunner` y `respx_mock`,
  reutilizando el helper de actividades JSON de `add-activity-list` (ampliado con los campos del
  detalle si no los tiene). Para "sin petición HTTP", `respx_mock` sin rutas y `calls` vacío.

Los escenarios de 401/403 de las reglas del proyecto no aplican: la ruta es pública. La spec exige
que no se envíen credenciales y cubre el 404 de actividad y el de un servidor equivocado.

## Risks / Trade-offs

- [El 404 de actividad y el de un servidor equivocado se distinguen solo por el cuerpo] → con JSON
  de la API se muestra `Activity not found`; con otro cuerpo, el mensaje genérico de HTTP 404.
- [El usuario espera ver plazas libres en el detalle] → no se muestran porque la API no las da; la
  fila se llama Capacity y el README lo aclara.
- [Organizer muestra `user-1`, no un nombre] → la API no expone usuarios por ID; aceptable.
- [Conflictos al editar `activities_cmd.py` y `api_client.py` a la vez que
  `add-activity-management`] → los cambios son aditivos (nuevas funciones y un subcomando); se
  resuelven al integrar.
- [Depende de `add-activity-list`] → la tarea 1.1 lo comprueba; hay que archivarlo antes que este,
  para que `activity-browsing` exista en `openspec/specs/`.
