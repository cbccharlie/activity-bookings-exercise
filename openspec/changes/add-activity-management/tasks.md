# Tasks

## 1. Requisito previo

- [ ] 1.1 Comprobar que están implementados `add-user-registration` (`ApiClient` con `_request()`, `ApiError` con `status_code`, `save_session`), `add-user-login` (`load_session`, `token_expiry`, helper de test para construir JWT) y `add-activity-list` (grupo `activities`, `Activity`, `parse_activity`, `_format_date`, `_format_price`), y que `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (activity-management + auth-session)

- [ ] 2.1 Añadir el parámetro `token` a `ApiClient` (cabecera `Authorization: Bearer <token>` solo si se indica); tests con respx de petición con token y sin él, pasando, y los tests de `register`, `login` y `list_activities` siguen pasando
- [ ] 2.2 Añadir `NewActivity` y `ActivityChanges` (frozen) con `to_json()` en camelCase, omisión de `duration`/campos `None`, sin `status`, e `is_empty()`; tests unitarios de los cuerpos generados, pasando
- [ ] 2.3 Implementar `create_activity()` (`POST /activities`, 201 parseado con `parse_activity`); tests con respx de ruta, cabecera y cuerpo, 201, 400 con `field_errors`, 401 (`status_code` 401) y 201 incompleto (`ApiResponseError`), pasando
- [ ] 2.4 Implementar `update_activity()` (`PUT /activities/<id>` con ID codificado); tests de cuerpo parcial, 200, 400, 403, 404 e ID con `/` codificado, pasando
- [ ] 2.5 Implementar `delete_activity()` (`DELETE /activities/<id>`, 204 sin cuerpo; añadir a `_request()` el modo sin cuerpo si hace falta); tests de 204, 403, 404 y 500, pasando, y el resto de tests del cliente siguen pasando

## 3. Sesión en rutas protegidas (auth-session)

- [ ] 3.1 Añadir `require_session(api_url)` a `session.py` (sin sesión, sesión inválida propagada, `api_url` distinta con las dos URL, `exp` pasado con `_now()` parcheable, `exp` ilegible permitido); tests en `tests/test_session.py` de cada caso, incluida la barra final como única diferencia, pasando
- [ ] 3.2 Crear `commands/_auth.py` con `authorized_client(settings)` y `login_hint()` (401 → mensaje de la API más `Run 'activity-bookings auth login' ...`; el resto de errores sin cambios); tests unitarios de los dos, pasando

## 4. Comando `activities create` (activity-management + auth-session)

- [ ] 4.1 Implementar `activities create` con sus opciones (obligatorias y `--duration`), orden configuración → sesión → petición dentro de `login_hint()`, y salida `Activity <id> created.` con la tabla sin cabecera; tests CLI de `create` en `activities --help`, cuerpo y cabecera enviados, `--duration`, precio decimal, salida de la actividad y token ausente de la salida, pasando
- [ ] 4.2 Añadir los tests CLI de error de `create`: opción obligatoria ausente y número no válido (código 2, sin HTTP), 400 con dos campos, API caída, 201 incompleto, sin sesión, sesión de otra API, token con `exp` en 2000 (sin HTTP) y 401 del servidor con la sugerencia y la sesión conservada; comprobar `Error:`, códigos y ausencia de `Traceback`, y que pasan

## 5. Comando `activities update` (activity-management + auth-session)

- [ ] 5.1 Implementar `activities update ACTIVITY_ID` con las opciones opcionales, rechazo sin campos (código 2, sin HTTP) y salida `Activity <id> updated.`; tests CLI de cuerpo parcial y cabecera, actividad actualizada, sin campos y sin ID, pasando
- [ ] 5.2 Añadir los tests CLI de error de `update`: 400 de `minParticipants`, 403 `You can only update your own activities`, timeout, sesión corrupta (ruta y sugerencia, sin HTTP) y token que no es JWT (sí se envía la petición); comprobar `Error:` y códigos, y que pasan

## 6. Comando `activities delete` (activity-management + auth-session)

- [ ] 6.1 Implementar `activities delete ACTIVITY_ID` con `--yes`/`-y` y `typer.confirm(..., default=False)` después de comprobar la sesión; tests CLI de ayuda del grupo (`list`, `create`, `update` y `delete`), borrado confirmado con `y`, `--yes` sin prompt, `n` e Intro (`Deletion cancelled.`, código 0, sin HTTP) y sin sesión sin prompt, pasando
- [ ] 6.2 Añadir los tests CLI de error de `delete`: 403 `You can only delete your own activities`, 404 `Activity not found` y 500 `API error 500: Failed to delete activity`, con `Error:`, código 1 y sin `Traceback`, pasando

## 7. Documentación

- [ ] 7.1 Documentar en el README `activities create`, `update` y `delete` (opciones, formato de `--date` con zona, confirmación y `--yes`, que se necesita sesión y qué pasa si caduca) con los avisos de Discrepancias 1a, 1b y 7 de `docs/api-reference.md`; verificar que `uv run activity-bookings activities <cmd> --help` coincide con lo documentado
- [ ] 7.2 Actualizar el layout de `AGENTS.md` con `session.py`, `commands/_auth.py` (helpers de rutas protegidas para los comandos) y los tests nuevos, y verificar que coincide con los ficheros existentes

## 8. Verificación final

- [ ] 8.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar `add-user-registration`, `add-user-login` y `add-activity-list` antes que este change.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
