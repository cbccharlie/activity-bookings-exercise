# Design

## Context

Hoy la CLI tiene el comando raíz (`cli.py`), la configuración (`config.py`: `Settings`,
`load_settings()`, `default_config_path()`), los errores (`errors.py`: `ActivityBookingsError`,
`ConfigError`, `handle_errors`) y las consolas Rich (`console.py`). No existe aún capa HTTP ni
dependencia `httpx`. Motivación y alcance en `proposal.md`; comportamiento exigido en
`specs/user-registration` y `specs/auth-session`. Contrato de `POST /users` en
`docs/api-reference.md` (Usuarios y autenticación): respuesta 201 sin envoltorio con
`user.id` numérico y `accessToken`; todos los errores son 400 con `{message, errors[]}`.

## Goals / Non-Goals

**Goals:**
- Una capa de cliente de API reutilizable por los próximos changes (login, actividades, reservas):
  composición de URL, timeout, traducción de errores HTTP y de red en un solo sitio.
- Un almacén de sesión que el login reutilice sin cambios.
- Comandos finos: el comando solo recoge entrada, llama al cliente y a la sesión, e imprime.

**Non-Goals:**
- Reintentos, logging o modo verbose.
- Enviar el token en peticiones (no hay rutas protegidas en este change).
- Un cliente asíncrono.

## Decisions

### Estructura

```
src/activity_bookings/
  api_client.py      # ApiClient (httpx), modelos User/AuthResult, parseo de respuestas
  session.py         # Session (dataclass), default_session_path(), save_session()
  errors.py          # + ApiError, ApiConnectionError, ApiResponseError, SessionError
  config.py          # + config_dir() compartido por config.toml y session.json
  commands/auth_cmd.py  # grupo `auth` con `register`
  cli.py             # app.add_typer(auth_cmd.app, name="auth")
tests/
  test_api_client.py  test_session.py  test_auth_cmd.py
```

### Cliente de API

`ApiClient(base_url: str, timeout: float = 10.0)` envuelve un `httpx.Client(base_url=..., timeout=...)`
y expone `register(username, email, password) -> AuthResult` (envía `terms: True`; la aceptación se
decide en el comando). Un método privado `_request()` centraliza la traducción:

| Situación | Excepción | Mensaje (tras `Error: `) |
|---|---|---|
| `httpx.ConnectError` | `ApiConnectionError` | `cannot connect to the API at <base_url>` |
| `httpx.TimeoutException` | `ApiConnectionError` | `the API at <base_url> did not respond in time` |
| Otro `httpx.HTTPError` | `ApiConnectionError` | `request to the API failed: <detalle>` |
| 4xx con JSON `{message, errors}` | `ApiError` | `<message>` y una línea `  - <field>: <message>` por error |
| 5xx con JSON | `ApiError` | `API error 500: <message>` |
| Error sin JSON válido o sin `message` de tipo texto | `ApiError` | `API returned HTTP <status> with an unexpected response` |
| 2xx con forma inesperada | `ApiResponseError` | `invalid response from the API: <qué falta>` |

`ApiError` guarda `status_code`, `message` y `field_errors: tuple[FieldError, ...]` para que el
login pueda distinguir el 401. Los modelos son dataclasses frozen: `User(id: int | str, username,
email)` y `AuthResult(user, access_token)`; `id` admite ambos tipos porque `POST /users` lo devuelve
numérico y el resto de la API usa `user-N` (Discrepancias de la referencia). El parseo valida tipos
a mano (sin pydantic: dos modelos pequeños no justifican la dependencia).

*Alternativa descartada:* `response.raise_for_status()` y capturar `HTTPStatusError` en los
comandos; reparte la traducción de errores por cada comando.

### Sesión

`Session(api_url, access_token, user: User)`, guardada como JSON en `config_dir() / "session.json"`
(mismo directorio que `config.toml`). La ruta no depende de `--config`: la opción cambia la
configuración, no dónde vive la sesión. `save_session()` escribe en un temporal del mismo
directorio creado con `tempfile.mkstemp()` (que lo crea con `0600`) y lo mueve con `os.replace()`, de modo que la
sustitución es atómica y los permisos quedan en `0600` también al sobrescribir. Cualquier `OSError`
se convierte en `SessionError` con la ruta. JSON con `json` de la stdlib (escribir TOML exigiría
una dependencia).

*Alternativas descartadas:* `$XDG_STATE_HOME` (más correcto según XDG, pero obliga a documentar y
aislar otro directorio sin beneficio en un cliente de formación); llavero del sistema (fuera de
alcance).

### Comando `auth register`

Orden: `load_settings(ctx.obj)` → pedir `--username`/`--email` si faltan (`typer.prompt`) →
contraseña con `typer.prompt(hide_input=True, confirmation_prompt=True)` → si no hay
`--accept-terms`, `typer.confirm(..., default=False)`; si se rechaza, `ActivityBookingsError` →
`ApiClient.register()` → `save_session()` → salida. Las opciones no usan `prompt=True` de Typer
porque esos prompts se ejecutan antes del cuerpo del comando y la configuración inválida se
detectaría después de teclear la contraseña. El comando usa `handle_errors`; si `save_session`
falla, se relanza como `SessionError` con el texto `account created, but the session could not be
saved to <path>: <causa>`.

Ejemplos:

```console
$ activity-bookings auth register --username Ana --email ana@example.com
Password:
Repeat for confirmation:
Do you accept the terms and conditions? [y/N]: y
Account created for Ana (ana@example.com).
Logged in. Session saved to /home/ana/.config/activity-bookings/session.json

$ activity-bookings auth register --username Ana --email ana@example --accept-terms
Password:
Repeat for confirmation:
Error: Validation failed
  - email: Email must be a valid email address

$ activity-bookings auth register --username Ana --email ana@example.com --accept-terms
Password:
Repeat for confirmation:
Error: cannot connect to the API at http://localhost:3000
```

### Dependencias

- `httpx` (runtime) y `respx` (dev): ambas forman parte del stack obligatorio del proyecto
  (`openspec/config.yaml`); se añaden con `uv add httpx` y `uv add --dev respx`. respx incluye la
  fixture de pytest `respx_mock`, que se usará en los tests.

### Tests

Los tests de CLI usan `CliRunner.invoke(..., input="secret1\nsecret1\ny\n")` para los prompts y
`respx_mock` para la API; comprueban el cuerpo enviado con `route.calls.last.request`. El fallo de
escritura de la sesión se provoca creando un fichero normal en la ruta del directorio
`activity-bookings`, que funciona igual aunque los tests se ejecuten como root (a diferencia de
`chmod`).

## Risks / Trade-offs

- [El token se guarda en texto plano] → permisos `0600` y escritura atómica; es aceptable para
  un cliente de formación y queda documentado como fuera de alcance.
- [Bug del servidor: `nextId` empieza en 1 y `POST /users` podría sobrescribir `user-1`
  (Discrepancias 1b)] → no se puede corregir desde el cliente; se documenta en el README.
- [El formato real de los mensajes de validación puede variar] → los tests usan los mensajes
  como datos y la CLI los muestra tal cual, sin depender de su texto.
- [Una respuesta de error HTML de Express (Discrepancias 8)] → cubierta por el caso "sin JSON
  válido".
