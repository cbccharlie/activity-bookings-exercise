# Tasks

## 1. Requisito previo

- [ ] 1.1 Comprobar que están implementados `add-user-registration`, `add-user-login`, `add-activity-list`, `add-activity-detail`, `add-activity-management` y `add-activity-booking`: existen `ApiClient(..., token=...)`, `_request(..., params=...)`, `Booking` y `parse_booking()`, `_format_date()`, `_format_price()`, `commands/_auth.py` (`authorized_client`, `login_hint`), el grupo `bookings` en `commands/bookings_cmd.py`, el fixture de sesión válida y el helper de JWT de los tests, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (my-bookings)

- [ ] 2.1 Añadir los modelos frozen `BookingActivity` y `BookingSummary` y `parse_booking_summary()` en `api_client.py` (reutiliza `parse_booking()`; `activity` validada a mano, `price` no booleano); tests en `tests/test_api_client.py` de reserva completa, sin `paymentStatus` (`pending`), sin `activity`, `activity` que no es un objeto, `price` booleano y `name` ausente (`ApiResponseError` con la reserva y el campo), pasando
- [ ] 2.2 Añadir `ApiClient.list_bookings(activity_id=None) -> list[BookingSummary]` (`GET /bookings` vía `_request()`, `activityId` solo si se indica); tests con respx de ruta, cabecera `Authorization` con token, parámetro `activityId` presente y ausente, 200 con `[]`, respuesta que no es lista y elemento inválido (`ApiResponseError`), 401 y 500 (`ApiError` con su `status_code`), pasando

## 3. Comando `bookings list` (my-bookings)

- [ ] 3.1 Si `_format_date()` y `_format_price()` no son ya importables desde `bookings_cmd.py` sin duplicarlos, moverlos a `commands/_format.py` y actualizar sus importaciones; verificar que los tests existentes de `activities` y `bookings create` siguen pasando sin cambios
- [ ] 3.2 Añadir el subcomando `list` al grupo `bookings` según el design (opción `--activity` con rechazo de blancos, `authorized_client`, `list_bookings()` dentro de `login_hint()` y `_deleted_activity_hint()`, tabla `My bookings` con ID, Activity, Date, Seats, Total, Payment y Activity status, recuento singular/plural y `No bookings found.`); tests CLI de «Subcomando de listado de reservas» (ayuda con `create` y `list`, API configurada) y de «Tabla de reservas» (varias reservas con totales `70.00` y `12.50`, fechas formateadas y orden de la API; una reserva con `1 booking`; sin `paymentStatus` con `pending`; lista vacía), pasando
- [ ] 3.3 Añadir los tests CLI de «Filtro por actividad» (`activityId=activity-2` en la query, sin `activityId` sin la opción, filtro sin resultados y `--activity " "` con código 2 y sin peticiones HTTP) y de «Listado con sesión» (cabecera `Bearer tok-123` y token ausente de la salida, sin sesión, `exp` en 2000 y sesión de otra API sin peticiones, 401 con la sugerencia de `auth login` y la sesión conservada), pasando
- [ ] 3.4 Añadir los tests CLI de «Errores del listado» (500 con `Failed to retrieve bookings` y `deleted activity`, respuesta no lista, reserva incompleta, 404 HTML, API caída y timeout), comprobando `Error:`, código 1 y ausencia de `Traceback`, pasando
- [ ] 3.5 Documentar `bookings list` en el README (opción `--activity`, columnas, que el total se calcula con el precio actual de la actividad, que el estado se muestra como pago y estado de la actividad, y el 500 por actividades borradas); verificar que `uv run activity-bookings bookings list --help` coincide con lo documentado

## 4. Verificación final

- [ ] 4.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar antes `add-user-registration`, `add-user-login`, `add-activity-list`, `add-activity-detail`, `add-activity-management` y `add-activity-booking`, para que `auth-session` exista en `openspec/specs/`.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
