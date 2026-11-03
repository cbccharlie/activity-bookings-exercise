# Tasks

## 1. Dependencias

- [ ] 1.1 Añadir `httpx` con `uv add httpx` y `respx` con `uv add --dev respx`, y verificar que `uv sync` termina sin errores y que `uv run python -c "import httpx, respx"` funciona

## 2. Cliente de API (user-registration)

- [ ] 2.1 Añadir a `errors.py` `ApiError` (con `status_code`, `message`, `field_errors` y el formato `message` + líneas `  - field: message`), `ApiConnectionError` y `ApiResponseError`; tests unitarios del texto de `ApiError` con y sin errores de campo pasando
- [ ] 2.2 Crear `api_client.py` con los modelos frozen `User` y `AuthResult` y su parseo desde el JSON de `POST /users` (lanzando `ApiResponseError` si falta `accessToken`, `user` o algún campo); tests en `tests/test_api_client.py` con respuesta válida, `id` numérico y de texto, y respuestas incompletas pasando
- [ ] 2.3 Implementar `ApiClient(base_url, timeout=10.0)` con `register(username, email, password)` (`POST /users` con `terms: true`) y la traducción centralizada de errores del design (conexión rechazada, timeout, 4xx con `{message, errors}`, 5xx, cuerpo no JSON); tests con respx de cada caso, incluido el cuerpo JSON enviado, pasando

## 3. Sesión local (auth-session)

- [ ] 3.1 Extraer `config_dir()` en `config.py` y hacer que `default_config_path()` lo use; verificar que los tests existentes de `tests/test_config.py` siguen pasando
- [ ] 3.2 Crear `session.py` con `Session` (frozen), `default_session_path()` y `save_session()` (JSON con `api_url`, `access_token`, `user {id, username, email}`, directorio creado si falta, temporal `0600` + `os.replace`) y añadir `SessionError` a `errors.py`; tests en `tests/test_session.py` de contenido, ruta con y sin `XDG_CONFIG_HOME`, permisos `0600`, sustitución de una sesión previa y `SessionError` cuando el directorio es un fichero, pasando

## 4. Comando `auth register` (user-registration + auth-session)

- [ ] 4.1 Crear `commands/auth_cmd.py` con el grupo `auth` (`no_args_is_help=True`) y registrarlo en `cli.py`; implementar `register` con `--username`, `--email`, `--accept-terms`, la carga de configuración antes de los prompts, prompts de los datos que falten, contraseña oculta con confirmación y confirmación de términos; tests CLI en `tests/test_auth_cmd.py` de ayuda (`auth` en la raíz, `register` en `auth --help`), datos por prompt, confirmación distinta, `--password` inexistente (código 2), términos rechazados sin petición HTTP y configuración inválida sin petición HTTP, pasando
- [ ] 4.2 Conectar `register` con `ApiClient` y `save_session()` y mostrar el resultado (`Account created for ...`, `Logged in. Session saved to ...`, sin token ni contraseña); tests CLI del registro correcto, cuerpo enviado a la `api_url` configurada, fichero de sesión creado con su contenido y sin la contraseña, pasando
- [ ] 4.3 Añadir los tests CLI de error: 400 de validación con varios campos, email ya registrado, 400 sin campos, API caída, timeout, 500, error no JSON, 201 sin `accessToken`, sesión previa intacta tras un fallo y fallo al guardar la sesión (mensaje con «account created» y la ruta); comprobar en todos `Error:`, código 1 y ausencia de `Traceback`, y que pasan

## 5. Documentación

- [ ] 5.1 Añadir al README, en la sección «ActivityBookings CLI», el uso de `auth register` (opciones, prompts, dónde se guarda la sesión y sus permisos) y el aviso del fallo conocido del servidor (Discrepancias 1 de `docs/api-reference.md`); verificar que `uv run activity-bookings auth register --help` muestra lo documentado
- [ ] 5.2 Actualizar el layout de `AGENTS.md` con `api_client.py`, `session.py`, `commands/auth_cmd.py` y los nuevos tests, y verificar que coincide con los ficheros existentes

## 6. Verificación final

- [ ] 6.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
