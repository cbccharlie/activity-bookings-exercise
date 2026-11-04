# Tasks

## 1. Requisito previo

- [x] 1.1 Comprobar que está implementado `add-activity-management` (y sus requisitos previos): existen `ApiClient(..., token=...)`, `_request()`, `parse_activity()`, `_activity_path()`, `commands/_auth.py` (`authorized_client`, `login_hint`), `ActivityStatus` y `_print_activity()` en `activities_cmd.py`, los helpers de sesión, JWT y actividad JSON de `tests/test_activities_cmd.py`, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (activity-management)

- [x] 2.1 Añadir `ApiClient.change_activity_status(activity_id, status) -> Activity` (`PATCH /activities/<id codificado>/status` con `{"status": ...}` vía `_request()` y `parse_activity()`); tests con respx de método, ruta, ID `a/b` enviado como `a%2Fb`, cuerpo, cabecera `Authorization` con token, 200 parseado, 200 incompleto como `ApiResponseError`, y 400, 403, 404 y 500 como `ApiError` con su `status_code` y mensaje, pasando

## 3. Comando `activities status` (activity-management)

- [x] 3.1 Añadir el subcomando `status ACTIVITY_ID NEW_STATUS` según el design (`NEW_STATUS` como `ActivityStatus`, rechazo de ID en blanco, `authorized_client`, `change_activity_status()` dentro de `login_hint()`, `_print_activity(..., "is now <status>")`), sin confirmación todavía; tests CLI de «Subcomandos de gestión de actividades» (ayuda con `status`, ampliando el test existente), «Cambio de estado de una actividad» (publicar con cabecera, cuerpo y token ausente de la salida; API configurada; ID con `/`) y «Argumentos del cambio de estado» (estado desconocido, falta el estado, faltan ambos, ID en blanco, con código 2 y sin peticiones), pasando
- [x] 3.2 Añadir `FINAL_STATUSES` y la confirmación `[y/N]` con `--yes`/`-y` para `cancelled` y `done`, después de comprobar la sesión; tests CLI de «Confirmación de los estados finales» (confirmada, rechazada, respuesta vacía con `done`, `--yes`, sin sesión sin preguntar) y uno que compruebe que `published` no pregunta, pasando
- [x] 3.3 Añadir los tests CLI de «Cambio de estado con sesión» (sin sesión, `exp` en 2000 y sesión de otra API sin peticiones, 401 con la sugerencia de `auth login` y la sesión conservada), pasando
- [x] 3.4 Añadir los tests CLI de «Errores del cambio de estado» (transición no permitida, desde estado final con `none (terminal state)`, 403, 404, 500, respuesta incompleta, 404 HTML, API caída y timeout), comprobando `Error:`, código 1 y ausencia de `Traceback`, pasando
- [x] 3.5 Documentar `activities status` en el README (argumentos, estados válidos y tabla de transiciones, confirmación de `cancelled`/`done` y `--yes`, que la API decide las transiciones y la propiedad, que cancelar no afecta a las reservas, y que con el fallo del login solo se pueden cambiar las actividades propias creadas tras `auth register`); verificar que `uv run activity-bookings activities status --help` coincide con lo documentado

## 4. Verificación final

- [x] 4.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- `docs/api-reference.md` ya se actualizó con el informe del `api-explorer` al preparar este change (orden de errores, estados finales, 401 y 500 de `PATCH /activities/:id/status`, y el error de `status` en `PUT`).
- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
