# Tasks

## 1. Requisito previo

- [x] 1.1 Comprobar que `add-user-registration` está implementado: existen `api_client.py` (`ApiClient`, `AuthResult`), `session.py` (`save_session`, `default_session_path`), `SessionError` y el grupo `auth` con `register`, y `uv run pytest` pasa. Si no, detenerse y avisar

## 2. Cliente de API (user-login)

- [x] 2.1 Añadir `ApiClient.login(email, password) -> AuthResult` (`POST /login` vía `_request()` y el parseo de `AuthResult`); tests con respx en `tests/test_api_client.py` del cuerpo enviado, respuesta 200, 401 `Invalid email or password` (`ApiError` con `status_code` 401), 400 con errores de campo y 200 sin `accessToken` (`ApiResponseError`), pasando

## 3. Sesión local (auth-session)

- [x] 3.1 Añadir `load_session()` a `session.py` (`None` si no existe; `SessionError` con la ruta y la sugerencia de `auth login` si no es JSON, no es un objeto o le faltan campos); tests en `tests/test_session.py` de ida y vuelta con `save_session`, fichero ausente, `not json` y sesión sin `access_token`, pasando
- [x] 3.2 Añadir `delete_session()` (`True`/`False` según existiera; `SessionError` con la ruta ante otro `OSError`); tests de borrado, fichero ausente, fichero corrupto borrado y fallo con un directorio en la ruta de `session.json`, pasando
- [x] 3.3 Añadir `token_expiry(token)` (lee `exp` del payload base64url del JWT sin verificar; `None` ante cualquier fallo) y un helper de test que construya JWT; tests de `exp` válido, token que no es JWT, payload no JSON y `exp` no entero, pasando

## 4. Comando `auth login` (user-login + auth-session)

- [x] 4.1 Extraer en `commands/auth_cmd.py` el helper `_save_session(result, api_url, done)` y usarlo en `register`; verificar que los tests existentes de `register` (incluido el fallo al guardar con «account created») siguen pasando
- [x] 4.2 Implementar `auth login` con `--email` (prompt si falta), configuración cargada antes de los prompts, contraseña oculta sin confirmación, `ApiClient.login()`, guardado y salida `Logged in as ... (...)`; tests CLI de ayuda (`login` en `auth --help`), cuerpo enviado a la `api_url` configurada, email por prompt, contraseña y token ausentes de la salida, `--password` inexistente (código 2), configuración inválida sin petición HTTP y contenido/permisos `0600` de la sesión, pasando
- [x] 4.3 Añadir los tests CLI de error del login: 401 `Invalid email or password` y `Authentication failed`, 400 con `--email ""`, API caída, timeout, 500, 200 sin `accessToken`, sesión previa sustituida tras éxito e intacta tras un 401, y fallo al guardar (mensaje con «logged in» y la ruta); comprobar `Error:`, código 1 y ausencia de `Traceback`, y que pasan
- [x] 4.4 Documentar `auth login` en el README (opciones, prompt de contraseña, sustitución de la sesión) con el aviso de Discrepancias 1 de `docs/api-reference.md` (el login puede fallar con usuarios de la semilla o recién registrados; usar la sesión del registro); verificar que `uv run activity-bookings auth login --help` coincide con lo documentado

## 5. Comando `auth logout` (auth-session)

- [x] 5.1 Implementar `auth logout` con `delete_session()` (`Logged out. Session removed from <path>` / `Not logged in.`); tests CLI de logout con sesión, sin sesión, con sesión corrupta, sin peticiones HTTP (respx sin rutas) y fallo al borrar (`Error:` con la ruta, código 1), pasando
- [x] 5.2 Documentar `auth logout` en el README, incluido que el token no se invalida en el servidor; verificar que `uv run activity-bookings auth logout --help` coincide

## 6. Comando `auth whoami` (auth-session)

- [x] 6.1 Implementar `auth whoami` con `load_session()` y `token_expiry()`, tabla Rich (User, Email, User ID, API URL, Token expires), `(expired)` más sugerencia de `auth login` y `unknown`; tests CLI de sesión vigente (`exp` en 2100), token caducado (`exp` en 2000), token `tok-123`, sin sesión (`Error:`, sugerencia, código 1), `not json` y sesión sin `access_token` (`Error:` con la ruta, código 1), token ausente de la salida y sin peticiones HTTP, pasando
- [x] 6.2 Documentar `auth whoami` en el README (qué muestra, que no consulta la API); verificar que `uv run activity-bookings auth whoami --help` coincide

## 7. Verificación final

- [x] 7.0 Actualizar el layout de `AGENTS.md` con las nuevas funciones de `session.py`, los subcomandos `login`, `logout` y `whoami` de `commands/auth_cmd.py` y `tests/jwt_helpers.py`, y verificar que coincide con los ficheros existentes
- [x] 7.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar `add-user-registration` antes que este change, para que `auth-session` exista en `openspec/specs/`.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
