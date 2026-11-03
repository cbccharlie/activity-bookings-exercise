# Tasks

## 1. Requisito previo

- [x] 1.1 Comprobar que están implementados `add-user-registration`, `add-user-login`, `add-activity-list`, `add-activity-detail` y `add-activity-management`: existen `ApiClient(..., token=...)`, `get_activity()`, `Activity`, `_format_date()`, `_format_price()`, `require_session()`, `commands/_auth.py` (`authorized_client`, `login_hint`), el fixture de sesión válida y el helper de JWT de los tests, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (activity-booking)

- [x] 2.1 Añadir el modelo frozen `Booking` y `parse_booking()` en `api_client.py` (`participants` entero o `float` entero, `paymentStatus` ausente → `pending`, `ApiResponseError` con el campo inválido); tests en `tests/test_api_client.py` de reserva completa, sin `paymentStatus`, `participants` `2.0`, `participants` booleano y cadena, `id` ausente y valor que no es un objeto, pasando
- [x] 2.2 Añadir `ApiClient.create_booking(activity_id, participants) -> Booking` (`POST /bookings` vía `_request()`); tests con respx de ruta, cuerpo JSON `{"activityId": ..., "participants": 2}` con entero, cabecera `Authorization` con token, 201, 400 `Capacity exceeded...`, 400 con `errors[]`, 402, 404 y 500 (`ApiError` con su `status_code` y mensaje) y 201 incompleto (`ApiResponseError`), pasando

## 3. Regla de reservabilidad (activity-booking)

- [x] 3.1 Crear `booking_rules.py` con `check_bookable(activity, now)` según el design (estado primero; fecha sin hora pasada si es anterior a hoy en UTC; con hora, pasada si `<= now`, sin zona = UTC; ilegible → error); tests en `tests/test_booking_rules.py` con `now` fijo: `draft`, `cancelled`, `done`, `sold-out` y `confirmed` rechazados con `not open for booking` y el estado; `published` con fecha futura con hora aceptada; fecha con hora pasada (`already took place`); fecha sin hora de ayer (rechazada), hoy y mañana (aceptadas); fecha con hora sin zona; fecha `pronto` (error con el ID), pasando

## 4. Comando `bookings create` (activity-booking)

- [x] 4.1 Crear `commands/bookings_cmd.py` con el grupo `bookings` y el subcomando `create` (argumento `ACTIVITY_ID`, `--participants/-p` con `min=1` y 1 por defecto, `--yes/-y`) y registrarlo en `cli.py`; implementar el flujo completo del design (validación de ID vacío, configuración, `authorized_client`, `get_activity`, `check_bookable` con `_now()`, confirmación, `create_booking` dentro de `login_hint()`, ficha de salida); tests CLI de los escenarios de «Subcomando de reserva» (ayuda del grupo y del subcomando, plazas por defecto, varias plazas como entero, API configurada) y de «Resultado de la reserva» (ficha con `Booking booking-1 created.`, nombre, ID, fecha, `70.00` y `paid`; respuesta incompleta sin `Traceback`), pasando
- [x] 4.2 Añadir los tests CLI de «Validación de la entrada» (sin ID, ID en blanco, `--participants 0` y `1.5`, todos con código 2 y sin peticiones HTTP) y de «Reserva con sesión» (cabecera `Bearer tok-123` y token ausente de la salida, sin sesión sin pregunta ni peticiones, `exp` en 2000 sin peticiones, 401 en `POST /bookings` con la sugerencia de `auth login` y la sesión conservada), pasando
- [x] 4.3 Añadir los tests CLI de «Solo actividades abiertas» (`draft`, `cancelled`, fecha 2000 con `already took place`, fecha de hoy sin hora con `_now()` parcheado a las 23:00 UTC, fecha `pronto`, 404 en el `GET`), comprobando en cada rechazo que la ruta respx de `POST /bookings` no tiene llamadas y el código 1, pasando
- [x] 4.4 Añadir los tests CLI de «Confirmación del cobro» (respuesta `y` con la pregunta que contiene `City Bike Tour`, `activity-2`, `2` y `70.00`; respuesta `n` con `Booking cancelled.`, código 0 y sin `POST`; `--yes` sin entrada y sin pregunta), pasando
- [x] 4.5 Añadir los tests CLI de «Errores de la reserva» (400 capacidad superada, 400 de validación con el campo, 402, 404 en el `POST`, 500, API caída y timeout), comprobando `Error:`, código 1 y ausencia de `Traceback`, pasando
- [x] 4.6 Documentar `bookings create` en el README (opciones, comprobación de estado y fecha en UTC, confirmación y `--yes`, total calculado por la CLI, que el cobro es inmediato y que no se puede cancelar, y que el 402 solo ocurre con importes múltiplos de 1000); verificar que `uv run activity-bookings bookings create --help` coincide con lo documentado

## 5. Verificación final

- [x] 5.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar antes `add-user-registration`, `add-user-login`, `add-activity-list`, `add-activity-detail` y `add-activity-management`, para que `auth-session` y `activity-browsing` existan en `openspec/specs/`.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
