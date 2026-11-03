# Proposal

## Why

La CLI aún no permite explorar el catálogo: para reservar o gestionar actividades, el usuario
primero tiene que ver qué actividades existen, su fecha, precio, capacidad y estado. `GET
/activities` es público, así que el listado se puede usar sin cuenta y es la base de los comandos
de detalle y de reservas.

## What Changes

- Nuevo grupo `activities` con el subcomando `activity-bookings activities list`, que consulta
  `GET /activities` y muestra una tabla Rich con ID, nombre, fecha, lugar, precio, capacidad
  (`maxParticipants`) y estado.
  - Por defecto muestra todas las actividades que devuelve la API, sea cual sea su estado.
  - `--search TEXT`: búsqueda por texto en el servidor (parámetro `q`: nombre, lugar y slug).
  - `--sort {date,price,name,location}` y `--order {asc,desc}`: orden en el servidor (`_sort` y
    `_order`). `--order` sin `--sort` es un error de uso.
  - `--status STATUS`: filtro en el cliente, porque la API no filtra por estado.
  - Si no hay resultados, lo indica y termina con código 0.
- Se amplía la capa de cliente de API con el modelo `Activity` y `ApiClient.list_activities()`.
- Errores (API caída, timeout, 5xx, 404 o respuesta inesperada) como `Error: ...` con código 1.

## Capabilities

### New Capabilities

- `activity-browsing`: exploración del catálogo público de actividades desde la CLI. En este change
  cubre el listado, la búsqueda, el orden y el filtro por estado; el detalle se añadirá después.

### Modified Capabilities

Ninguna.

## Fuera de alcance

- Detalle de una actividad (`GET /activities/:id`) y búsqueda exacta por `slug`.
- Plazas libres: la API no las expone (ver `docs/api-reference.md`, Reglas).
- Paginación (la API no la ofrece) y filtros por fecha o precio.
- Enviar el token: la ruta es pública y el listado no usa la sesión.
- Crear, editar, borrar o cambiar el estado de actividades.
- Salida en JSON u otros formatos.

## Impact

- **Requisito previo:** `add-user-registration` implementado, porque se reutilizan su `ApiClient`,
  `_request()` y la traducción de errores (`ApiError`, `ApiConnectionError`, `ApiResponseError`).
  No depende de `add-user-login`.
- **Código:** `api_client.py` (`Activity`, `list_activities`), nuevo `commands/activities_cmd.py`
  y registro del grupo en `cli.py`.
- **Tests:** nuevos con respx. **Dependencias:** ninguna nueva.
- **Documentación:** README (uso de `activities list`) y layout de `AGENTS.md`.
