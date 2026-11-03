# Tasks

## 1. Requisito previo

- [ ] 1.1 Comprobar que está implementado `add-booking-list` (y sus requisitos previos): existen `ApiClient(..., token=...)`, `_request()`, `Booking`, `BookingActivity`, `BookingSummary`, `parse_booking_summary()`, `ApiClient.list_bookings()`, el grupo `bookings` con `create` y `list`, `_deleted_activity_hint()`, `commands/_auth.py` (`authorized_client`, `login_hint`), `_format_date()`, `_format_price()`, `_format_duration()`, el fixture de sesión válida, el helper de JWT y el helper de reservas JSON de los tests, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (my-bookings)

- [ ] 2.1 Añadir el modelo frozen `BookingDetail` y `parse_booking_detail()` en `api_client.py` (reutiliza `parse_booking_summary()`; `paymentId` opcional, `activity.location` cadena, `activity.duration` entero no booleano con `float` entero aceptado); tests en `tests/test_api_client.py` de reserva completa, sin `paymentId`, `paymentId` `null`, `duration` `120.0`, `duration` booleano, `location` ausente y dato que no es objeto (`ApiResponseError`), pasando
- [ ] 2.2 Añadir `ApiClient.get_booking(booking_id) -> BookingDetail` (`GET /bookings/<id codificado>` vía `_request()`); tests con respx de ruta, ID `a/b` enviado como `a%2Fb`, cabecera `Authorization` con token, 200, y 401, 404 y 500 como `ApiError` con su `status_code`, pasando

## 3. Comando `bookings show` (my-bookings)

- [ ] 3.1 Parametrizar el texto de `_deleted_activity_hint()` según el design sin cambiar el mensaje de `bookings list`; verificar que los tests existentes de `bookings list` siguen pasando sin cambios
- [ ] 3.2 Añadir el subcomando `show BOOKING_ID` al grupo `bookings` según el design (rechazo de ID en blanco, `authorized_client`, `get_booking()` dentro de `login_hint()` y `_deleted_activity_hint()`, ficha sin cabecera con ID, Activity, Date, Duration, Location, Seats, Price, Total, Payment, Payment ID opcional, Activity status y Booked at); ampliar el helper de reservas JSON con `paymentId`, `duration` y `location` si hace falta; tests CLI de «Subcomando de detalle de reserva» (ayuda con `create`, `list` y `show`, API configurada, ID con `/`, ID en blanco y ausente con código 2 sin peticiones) y de «Ficha de la reserva» (reserva completa con `120 min`, `35.00`, `70.00`, `payment-1` y `2100-11-03 10:00 UTC`; sin `paymentStatus` ni `paymentId` con `pending` y sin `Payment ID`), pasando
- [ ] 3.3 Añadir los tests CLI de «Detalle con sesión» (cabecera `Bearer tok-123` y token ausente de la salida, sin sesión, `exp` en 2000 y sesión de otra API sin peticiones, 401 con la sugerencia de `auth login` y la sesión conservada), pasando
- [ ] 3.4 Añadir los tests CLI de «Errores del detalle de reserva» (404 `Booking not found`, 500 con `Failed to retrieve booking` y `deleted activity`, respuesta que no es objeto, reserva incompleta, 404 HTML, API caída y timeout), comprobando `Error:`, código 1 y ausencia de `Traceback`, pasando
- [ ] 3.5 Documentar `bookings show` en el README (argumento `BOOKING_ID`, filas de la ficha, que el 404 cubre también reservas de otros usuarios, que el total usa el precio actual y el 500 por actividades borradas); verificar que `uv run activity-bookings bookings show --help` coincide con lo documentado

## 4. Verificación final

- [ ] 4.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar antes `add-booking-list` (y los changes de los que depende), para que `my-bookings` exista en `openspec/specs/`.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
