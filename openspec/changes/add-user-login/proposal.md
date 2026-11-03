# Proposal

## Why

Con `add-user-registration`, la única forma de obtener un JWT es crear una cuenta nueva. Un usuario
que ya tiene cuenta, o cuyo token ha caducado (24 h), necesita iniciar sesión. También tiene que
poder ver con qué cuenta está trabajando y cerrar la sesión local antes de que lleguen los comandos
protegidos (reservas y gestión de actividades).

## What Changes

- Nuevo subcomando `activity-bookings auth login`, que inicia sesión con `POST /login`.
  - El email se pasa con `--email` o se pide de forma interactiva.
  - La contraseña se pide siempre por prompt oculto y nunca se acepta como opción.
  - Si el login es correcto, guarda la sesión igual que el registro y sustituye la anterior.
  - Si falla, la sesión existente queda intacta.
  - Las credenciales incorrectas (401) y la validación (400) se muestran como `Error: ...` con
    código de salida 1.
- Nuevo subcomando `activity-bookings auth logout`, que borra el fichero de sesión local. No llama a
  la API porque no existe un endpoint de logout. Si no hay sesión, informa y termina con código 0.
- Nuevo subcomando `activity-bookings auth whoami`, que muestra a partir de la sesión local el
  usuario, el email, la URL de la API y la caducidad del token (leída del JWT sin verificarlo).
  - Si no hay sesión, termina con un error.
  - También termina con un error si el fichero de sesión está corrupto.
- Se amplían la capa de cliente con `ApiClient.login()` y el módulo de sesión con
  `load_session()` y `delete_session()`.

## Capabilities

### New Capabilities

- `user-login`: el inicio de sesión desde la CLI contra `POST /login`. Cubre las entradas, lo que se
  envía, la salida y los errores.

### Modified Capabilities

- `auth-session`: la crea `add-user-registration` y este change le añade requisitos.
  - Se añaden el guardado de la sesión tras el login, el borrado de la sesión (`auth logout`) y la
    consulta de la sesión actual (`auth whoami`).
  - También se añade la lectura del fichero de sesión, incluido el caso de un fichero corrupto.
  - Se escriben como requisitos ADDED, porque la capacidad aún no está archivada en
    `openspec/specs/`.

## Fuera de alcance

- Enviar el token en las rutas protegidas y gestionar el 401 de token caducado en ellas.
- Invalidar el token en el servidor. No hay endpoint para hacerlo, así que el token sigue siendo
  válido hasta que caduca.
- Comprobar el token contra la API en `whoami`. No hay endpoint de perfil.
- Verificar la firma del JWT. La CLI no conoce el secreto.
- Rodear el fallo conocido del servidor por el que el login falla con usuarios de la semilla o
  recién registrados (Discrepancias 1 de `docs/api-reference.md`). Solo se documenta.
- Refresh tokens, varias cuentas o perfiles, y llavero del sistema.

## Impact

- **Requisito previo:** `add-user-registration` tiene que estar implementado, porque este change
  reutiliza su `ApiClient`, sus modelos `User` y `AuthResult`, `save_session()` y el grupo `auth`.
- **Código:** se modifican `api_client.py` (`login`), `session.py` (`load_session` y
  `delete_session`), `commands/auth_cmd.py` (`login`, `logout` y `whoami`) y `errors.py` si hace
  falta.
- **Tests:** se añaden con respx.
- **Dependencias:** ninguna nueva.
- **Documentación:** el README, con el uso de los tres subcomandos y el aviso del fallo del servidor.
