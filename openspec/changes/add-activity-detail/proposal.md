# Proposal

## Why

`activities list` muestra un resumen de cada actividad, pero deja fuera datos que el usuario
necesita para decidir si reserva: duración, mínimo de participantes, organizador y fechas de alta y
modificación. `GET /activities/:id` es público y devuelve la actividad completa, así que el detalle
se puede consultar sin cuenta y es el paso previo natural a los comandos de reservas.

## What Changes

- Nuevo subcomando `activity-bookings activities show ACTIVITY_ID`, que consulta
  `GET /activities/:id` y muestra una tabla Rich de dos columnas (campo y valor) con ID, nombre,
  slug, fecha, duración, lugar, precio por plaza, participantes mínimos, capacidad, estado,
  organizador, fecha de alta y, si existe, de última modificación.
- Funciona sin sesión y no envía credenciales.
- Un ID vacío o en blanco es un error de uso (código 2) sin llamar a la API.
- Se amplía la capa de cliente de API con el modelo `ActivityDetail` y
  `ApiClient.get_activity(activity_id)`.
- Errores (actividad inexistente, API caída, timeout, 5xx o respuesta inesperada) como
  `Error: ...` con código 1.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `activity-browsing`: se añade el detalle de una actividad por su ID. La capacidad la crea
  `add-activity-list`, que ya anunciaba que el detalle llegaría después.

## Fuera de alcance

- Plazas libres u ocupadas: la API no las expone (`docs/api-reference.md`, Reglas 1).
- Buscar la actividad por `slug` o por nombre; solo se admite el ID.
- Mostrar las reservas de la actividad, reservar desde el detalle o indicar si es reservable.
- Mostrar el nombre del organizador: la API solo devuelve su `userId`.
- Indicar si la actividad es mía (comparar con la sesión) y las transiciones de estado posibles.
- Salida en JSON u otros formatos.

## Impact

- **Requisitos previos:** `add-user-registration` y `add-activity-list` implementados (grupo
  `activities`, modelo `Activity`, `parse_activity()`, `_format_date()` y `_format_price()`). No
  depende de `add-user-login` ni de `add-activity-management`.
- **Código:** `api_client.py` (`ActivityDetail`, `get_activity`) y `commands/activities_cmd.py`.
- **Tests:** nuevos con respx. **Dependencias:** ninguna nueva.
- **Documentación:** README (uso de `activities show`).
