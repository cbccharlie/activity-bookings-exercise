# Tasks

## 1. Requisito previo

- [ ] 1.1 Comprobar que `add-user-registration` está implementado: existen `api_client.py` (`ApiClient` con `_request()`), `ApiError`, `ApiConnectionError` y `ApiResponseError` en `errors.py`, `respx` instalado, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (activity-browsing)

- [ ] 2.1 Añadir a `api_client.py` el modelo frozen `Activity` (`id`, `name`, `date`, `location`, `price`, `max_participants`, `status`) y `parse_activity()` con validación manual y `ApiResponseError` que nombra la actividad y el campo; tests en `tests/test_api_client.py` de actividad válida, `price` entero y decimal, campos extra y `updatedAt` ausente, `name` ausente y `price` booleano, pasando
- [ ] 2.2 Implementar `ApiClient.list_activities(search, sort, order)` (`GET /activities`; `q` solo con `search`; `_sort` y `_order` solo con `sort`; añadir `params` opcional a `_request()` si no existe) y el error `expected a list of activities`; tests con respx de petición sin parámetros, con `q`, con `_sort`/`_order`, sin cabecera `Authorization`, respuesta `{"activities": []}`, elemento inválido y 500, pasando, y los tests de `register` siguen pasando

## 3. Comando `activities list` (activity-browsing)

- [ ] 3.1 Crear `commands/activities_cmd.py` con el grupo `activities` (`no_args_is_help=True`) y el subcomando `list` sin opciones, registrarlo en `cli.py`, y mostrar la tabla (ID, Name, Date, Location, Price, Capacity, Status), la línea `N activities` y `No activities found.`; tests CLI en `tests/test_activities_cmd.py` de ayuda, petición a la `api_url` configurada, listado con varias actividades en el orden recibido, todos los estados por defecto, listado vacío y configuración inválida sin petición HTTP, pasando
- [ ] 3.2 Añadir `_format_date()` y `_format_price()` (solo fecha tal cual, fecha y hora como `YYYY-MM-DD HH:MM UTC`, fecha no interpretable tal cual, precio con dos decimales); tests unitarios de las funciones y CLI de los escenarios «Fecha con hora» y «Fecha que no se puede interpretar», pasando
- [ ] 3.3 Añadir `--search` (rechazo de vacío o en blanco con código 2), `--sort` y `--order` (`StrEnum`, `asc` por defecto, `--order` sin `--sort` con código 2) validados antes de cargar la configuración; tests CLI de los escenarios de «Búsqueda por texto» y «Orden del listado», incluidos los valores inválidos sin petición HTTP, pasando
- [ ] 3.4 Añadir `--status` (`StrEnum` con los seis estados, filtro en el cliente conservando el orden, sin enviarlo a la API); tests CLI de solo publicadas, ninguna con ese estado y estado no válido (código 2, sin petición HTTP), pasando
- [ ] 3.5 Añadir los tests CLI de «Errores al consultar el listado»: API caída, timeout, 500 con `Failed to retrieve activities`, 404 HTML, respuesta que no es lista y actividad sin `name`; comprobar en todos `Error:`, código 1 y ausencia de `Traceback`, y que pasan

## 4. Documentación

- [ ] 4.1 Documentar `activities list` en la sección «Uso» del README (opciones, que muestra todas las actividades por defecto, que `--status` filtra en el cliente y que Capacity es la capacidad total, no las plazas libres); verificar que `uv run activity-bookings activities list --help` coincide con lo documentado
- [ ] 4.2 Actualizar el layout de `AGENTS.md` con `commands/activities_cmd.py` y `tests/test_activities_cmd.py`, y verificar que coincide con los ficheros existentes

## 5. Verificación final

- [ ] 5.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar `add-user-registration` antes que este change.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
