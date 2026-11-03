# Proposal

## Why

La CLI solo sabe mostrar su configuración: no hay forma de crear una cuenta en la API ni de obtener
el JWT que exigen las rutas protegidas (reservas y gestión de actividades). El registro es el
primer paso de cualquier flujo y, según `docs/api-reference.md` (Discrepancias, punto 1), el login
del servidor probablemente falle con usuarios recién creados, así que el token que devuelve
`POST /users` es hoy la forma fiable de empezar a trabajar.

## What Changes

- Nuevo subcomando `activity-bookings auth register` que registra un usuario con `POST /users`.
  - Pide por opción o, si faltan, de forma interactiva: `--username`, `--email`, contraseña
    (siempre por prompt oculto con confirmación) y aceptación de términos (`--accept-terms` o
    confirmación interactiva).
  - Si no se aceptan los términos, no llama a la API.
  - Muestra el usuario creado y avisa de que la sesión queda iniciada.
- Persistencia local de la sesión: el `accessToken` devuelto se guarda en un fichero de sesión
  del usuario, con permisos restringidos, junto a la URL de la API y los datos del usuario.
- Primera versión de la capa de cliente de API (httpx) con traducción de errores:
  validación 400 con detalle por campo, email ya registrado, API inaccesible, respuestas 5xx o
  inesperadas. Todo se muestra como `Error: ...` con código de salida 1, sin trazas.
- Se añaden `httpx` (dependencia) y `respx` (dev), ambos del stack obligatorio.

## Capabilities

### New Capabilities

- `user-registration`: alta de usuarios desde la CLI contra `POST /users`, entradas, salida y
  errores del registro.
- `auth-session`: almacenamiento local de la sesión (token JWT y datos del usuario): ubicación,
  formato, permisos y sobrescritura. Lo reutilizarán el login y las rutas protegidas.

### Modified Capabilities

Ninguna. `cli-shell` ya cubre el formato `Error:` y los códigos de salida; el nuevo grupo `auth`
solo aparece en la lista de subcomandos.

## Fuera de alcance

- Login (`POST /login`), logout y consulta de la sesión actual (`whoami`): changes posteriores.
- Enviar el token en las rutas protegidas y gestionar el 401 de token caducado.
- Validación local de email y contraseña: las reglas las aplica el servidor y la CLI muestra sus
  errores tal cual. Solo se exige localmente la aceptación de términos.
- Cifrado del token o uso del llavero del sistema.
- Soporte de varias cuentas o perfiles simultáneos.

## Impact

- Código nuevo: `api_client.py` (cliente HTTP y errores de API), `session.py` (sesión local),
  `commands/auth_cmd.py` (grupo `auth`), registro del grupo en `cli.py`, nuevas subclases de
  `ActivityBookingsError` en `errors.py`.
- Tests nuevos con respx; `pyproject.toml` y `uv.lock` (vía `uv add`).
- `AGENTS.md` (layout) y README (uso de `auth register`).
