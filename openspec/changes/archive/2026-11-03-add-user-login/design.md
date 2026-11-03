# Design

## Context

Este change se apoya en `add-user-registration` y supone que ya está implementado. De ese change
reutiliza estas piezas:

- `api_client.py`:
  - `ApiClient(base_url, timeout)`.
  - `_request()`, con la traducción centralizada de errores a `ApiError`, `ApiConnectionError` y
    `ApiResponseError`.
  - Los modelos frozen `User` y `AuthResult`, y el parseo de `{user, accessToken}`.
- `session.py`:
  - `Session(api_url, access_token, user)`.
  - `default_session_path()`, que apunta a `config_dir() / "session.json"`.
  - `save_session()`, que escribe un temporal con permisos `0600` y lo mueve con `os.replace`.
- `errors.py`: `SessionError`.
- `commands/auth_cmd.py`: el grupo `auth` con `register`, registrado en `cli.py`.

Según `docs/api-reference.md`, `POST /login` responde 200 con la misma forma que `POST /users`.
Sus errores son 400 de validación con `errors[]` y 401 con `errors: []`. El JWT lleva `exp` y caduca
a las 24 h. No hay endpoints de logout ni de perfil.

## Goals / Non-Goals

**Goals:**
- Login, logout y whoami como comandos finos, sin duplicar la traducción de errores ni la escritura
  de la sesión.
- Una API de sesión completa (`save`, `load` y `delete`) que los comandos protegidos de los próximos
  changes puedan usar tal cual.

**Non-Goals:**
- Comprobar en `whoami` que la `api_url` de la sesión coincide con la configuración actual. Se
  abordará con las rutas protegidas.
- Avisos o rodeos específicos del fallo conocido del login en el servidor.

## Decisions

### Cliente de API

`ApiClient.login(email, password) -> AuthResult` envía `POST /login` a través de `_request()` y usa
el mismo parseo que `register()`. Así, el 401 sale como `ApiError(status_code=401,
message="Invalid email or password")` por la ruta genérica de 4xx sin tocar la tabla de errores, y
el mensaje es exactamente el de la API. No se añade ningún texto propio del cliente.

### Sesión

- **`load_session(path=None) -> Session | None`.**
  - Devuelve `None` si el fichero no existe.
  - Lanza `SessionError(f"invalid session file {path}: {causa}; run 'activity-bookings auth login'
    to start a new session")` en estos casos: JSON inválido, raíz que no es un objeto, campos
    ausentes o con un tipo incorrecto, o un `OSError` al leer.
  - La validación es manual, igual que en `api_client.py`, y reutiliza el parseo de `User`.
- **`delete_session(path=None) -> bool`.**
  - Hace `unlink()`. Devuelve `True` si ha borrado el fichero y `False` ante `FileNotFoundError`.
  - Cualquier otro `OSError` se convierte en `SessionError` con la ruta.
  - No lee el contenido, así que también borra sesiones corruptas.
- **`token_expiry(token: str) -> datetime | None`.**
  - Toma el segundo segmento del JWT, lo decodifica en base64url (añadiendo el relleno), lo parsea
    como JSON y lee `exp` como entero.
  - Devuelve un `datetime` en UTC, o `None` ante cualquier fallo.
  - No verifica la firma, porque la CLI no conoce el secreto. Solo se usa para informar.

*Alternativa descartada:* PyJWT, porque añadiría una dependencia para leer un único campo sin poder
verificar la firma.

### Comandos

- **`login`.**
  - Orden de los pasos:
    1. `load_settings(ctx.obj)`.
    2. `--email`, o `typer.prompt("Email")` si falta.
    3. `typer.prompt("Password", hide_input=True)`, sin confirmación.
    4. `ApiClient.login()`.
    5. `save_session()`.
    6. Salida.
  - Igual que en `register`, no se usa `prompt=True` de Typer. Así se valida la configuración antes
    de pedir la contraseña.
  - El guardado y su error se extraen a un helper común con `register`:
    `_save_session(result, api_url, done: str)`.
  - Si el guardado falla, el error es `SessionError(f"{done}, but the session could not be saved to
    {path}: {causa}")`. `done` vale `"account created"` en `register` y `"logged in"` en `login`.
- **`logout`.**
  - Llama a `delete_session()`.
  - Si devuelve `True`, muestra `Logged out. Session removed from <path>`.
  - Si devuelve `False`, muestra `Not logged in.`. En los dos casos termina con código 0.
  - No carga la configuración, porque no la necesita.
- **`whoami`.**
  - Llama a `load_session()`.
  - Si devuelve `None`, lanza `ActivityBookingsError("not logged in; run 'activity-bookings auth
    login' or 'activity-bookings auth register'")`.
  - Muestra una tabla Rich sin cabecera, igual que el comando `config`, con estas filas: User, Email,
    User ID, API URL y Token expires.
  - Si el token ha caducado, añade ` (expired)` a la fecha y una línea con la sugerencia de volver a
    hacer login.
  - Si la caducidad no se puede leer, muestra `unknown`.
  - Para poder probar la caducidad, la hora actual se obtiene con `datetime.now(UTC)` dentro de una
    función pequeña que los tests pueden parchear, aunque basta con usar `exp` lejanos (2000 y
    2100).

Ejemplos:

```console
$ activity-bookings auth login --email m@f.c
Password:
Logged in as Mark Musk (m@f.c).
Session saved to /home/ana/.config/activity-bookings/session.json

$ activity-bookings auth login --email m@f.c
Password:
Error: Invalid email or password

$ activity-bookings auth whoami
User           Mark Musk
Email          m@f.c
User ID        1
API URL        http://localhost:3000
Token expires  2026-11-04 10:15 UTC

$ activity-bookings auth whoami
...
Token expires  2026-11-02 10:15 UTC (expired)
Your session has expired. Run 'activity-bookings auth login' to start a new one.

$ activity-bookings auth logout
Logged out. Session removed from /home/ana/.config/activity-bookings/session.json

$ activity-bookings auth logout
Not logged in.

$ activity-bookings auth whoami
Error: not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'
```

### Dependencias

No se añade ninguna.

### Tests

- Se amplían `tests/test_api_client.py`, `tests/test_session.py` y `tests/test_auth_cmd.py`.
- Un helper de test construye JWT sin firma válida, con la forma `base64url(header).base64url({"exp":
  N}).sig`.
- Para provocar un fallo al borrar la sesión, se crea un directorio en la ruta de `session.json`.
  `unlink()` falla con `OSError` también si los tests se ejecutan como root.
- Para provocar un fallo al guardar, se usa el mismo truco que en el registro: un fichero normal en
  la ruta del directorio `activity-bookings`.

## Risks / Trade-offs

- [El fallo del servidor (Discrepancias 1) hace que el login probablemente responda 401 con los
  usuarios de la semilla y con los recién registrados] → La CLI muestra el error de la API tal cual
  y el README lo documenta. Se recomienda trabajar con la sesión que deja `auth register`.
- [`logout` no invalida el token y una copia del token sigue siendo válida hasta que caduca] → No
  hay endpoint para invalidarlo. Se documenta en el README.
- [`whoami` lee `exp` sin verificar la firma] → Solo se usa para informar. La validez real la decide
  el servidor en las rutas protegidas.
- [Este change depende de `add-user-registration`] → La tarea 1.1 lo comprueba antes de empezar.
  Hay que archivar primero el registro para que `auth-session` exista al archivar este change.
