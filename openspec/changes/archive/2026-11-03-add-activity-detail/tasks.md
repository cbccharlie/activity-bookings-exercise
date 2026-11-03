# Tasks

## 1. Requisito previo

- [x] 1.1 Comprobar que `add-activity-list` está implementado: existen en `api_client.py` `Activity`, `parse_activity()` y `_request()`; en `commands/activities_cmd.py` el grupo `activities`, `_format_date()` y `_format_price()`; y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (activity-browsing)

- [x] 2.1 Añadir a `api_client.py` el modelo frozen `ActivityDetail` (compone `Activity` y añade `slug`, `duration`, `min_participants`, `user_id`, `created_at`, `updated_at`) y `parse_activity_detail()` reutilizando `parse_activity()`; tests en `tests/test_api_client.py` de actividad completa, sin `updatedAt`, `updatedAt` `null`, `duration` `120.0`, `duration` ausente y booleano, `userId` no cadena y JSON que no es objeto, pasando, y los tests de `parse_activity` siguen pasando
- [x] 2.2 Implementar `ApiClient.get_activity(activity_id)` (`GET /activities/<id>` con `quote(id, safe="")`, sin `Authorization`, parseo con `parse_activity_detail()`); tests con respx de ruta, ID `a/b c` codificado como `a%2Fb%20c`, ausencia de `Authorization`, 404 `Activity not found` y 500 `Failed to retrieve activity`, pasando

## 3. Comando `activities show` (activity-browsing)

- [x] 3.1 Añadir el subcomando `show ACTIVITY_ID` a `commands/activities_cmd.py` con la validación de ID vacío o en blanco (código 2) antes de cargar la configuración, `_format_duration()` y la ficha sin cabecera (ID, Name, Slug, Date, Duration, Location, Price, Min participants, Capacity, Status, Organizer, Created y Updated solo si existe); tests CLI en `tests/test_activities_cmd.py` de los escenarios de «Subcomando de detalle de actividad», «Detalle público sin sesión» y «Ficha de la actividad», pasando, y los tests de `activities list` siguen pasando
- [x] 3.2 Añadir los tests CLI de «Errores al consultar el detalle»: actividad inexistente, API caída, timeout, 500, 404 HTML, respuesta que no es objeto y actividad sin `duration`; comprobar en todos `Error:`, código 1 y ausencia de `Traceback`, y que pasan

## 4. Documentación

- [x] 4.1 Documentar `activities show` en la sección «Uso» del README (argumento, que es público, filas de la ficha y que Capacity es la capacidad total, no las plazas libres); verificar que `uv run activity-bookings activities show --help` coincide con lo documentado; añadir `show` a la línea de `activities_cmd.py` del layout de `AGENTS.md`

## 5. Verificación final

- [x] 5.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar `add-user-registration` y `add-activity-list` antes que este change.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
