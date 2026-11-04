# Programación Inteligente
Documentación para el curso de programación inteligente

Domina las nuevas primitivas de programación con IA para desarrollos más productivos y de calidad; 
Pasa del Vibe Coding a la Spec-Driven Development.

---

## Sample project : Astro-Bookings
API mínima en TypeScript y Express .

- **Ejemplo de proyecto**: [Astro-Bookings-Demo](https://github.com/Programacion-Inteligente/activity-bookings-express)

---

## Exercise project : Astro-Bookings-Client
Aplicación cliente para interactuar con la API de Astro-Bookings.
En cualquier lenguaje/framework de elección (e.g., React, Vue, Angular, o una CLI en Python/Node.js). 
Incluso una aplicación de consola o web en Java o C#.

- [Exercise project : Astro-Bookings-Client](./astrobookings-cli.briefing.md)

Por supuesto, puedes desarrollarlo con cualquier herramienta de IA que te guste.
- VSCode + GitHub Copilot
- Cursor
- ClaudeCode
- Antigravity
- etc.

---

## ActivityBookings CLI

Cliente de consola en Python para la API ActivityBookings (comando `activity-bookings`).

### Requisitos

- Python 3.12 o superior.
- [uv](https://docs.astral.sh/uv/getting-started/installation/), por ejemplo:
  `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Instalación

```bash
uv sync
```

### Uso

```bash
uv run activity-bookings --help      # ayuda y lista de subcomandos
uv run activity-bookings --version   # versión instalada
uv run activity-bookings config      # configuración efectiva (URL de la API y su origen)
uv run activity-bookings --config ./custom.toml config   # usar otro fichero de configuración
```

### Modo interactivo

```bash
uv run activity-bookings                              # abre el menú
uv run activity-bookings --config ./custom.toml       # el menú usa esa configuración
```

- Sin subcomando y en un terminal, se abre un menú que se recorre con las flechas y Enter. Si la
  entrada o la salida no son un terminal (un script, una tubería), muestra la ayuda como siempre.
- Opciones, agrupadas: actividades (listar, ver, crear, modificar, borrar, cambiar estado), reservas
  (reservar, mis reservas, ver reserva), cuenta (registro, login, logout, whoami), configuración y
  `Exit`. Los títulos de sección (`── Activities ──`...) se muestran en gris y el cursor se los
  salta. Encima del menú se indica la sesión (`Logged in as Ana` / `Not logged in`).
- Cada opción pide sus datos y ejecuta el subcomando equivalente, con su misma validación, errores
  y salida. Los datos opcionales se dejan vacíos para omitirlos (en `Update an activity`, vacío
  conserva el valor). Tras cada acción, también si falla, vuelve al menú.
- Borrar y pasar a `cancelled`/`done` piden confirmación en el menú. Reservar pide la confirmación
  con el total del propio `bookings create`, y las contraseñas se piden igual que fuera del menú.
- Esc o Ctrl+C en un dato abandonan esa acción; en el menú, o eligiendo `Exit`, salen (código 0).

### Registro de usuarios

```bash
uv run activity-bookings auth register --username Ana --email ana@example.com --accept-terms
```

- `--username` y `--email`: si se omiten, se piden de forma interactiva.
- La contraseña se pide siempre por un prompt oculto, con confirmación; no existe opción
  `--password`.
- `--accept-terms`: acepta los términos y condiciones. Sin ella se pregunta, y si se rechazan no
  se llama a la API.

Si el registro va bien, la sesión queda iniciada: el token JWT devuelto, la URL de la API y los
datos del usuario se guardan en `$XDG_CONFIG_HOME/activity-bookings/session.json` (por defecto
`~/.config/activity-bookings/session.json`), con permisos `0600`. Cada registro correcto sustituye
la sesión anterior; uno fallido la deja intacta. El token se guarda en texto plano.

> **Fallo conocido del servidor** (punto 1 de «Discrepancias y dudas» en
> `docs/api-reference.md`): por el orden de inicialización de la API, un usuario recién
> registrado probablemente no pueda hacer login, y el alta podría sobrescribir el usuario
> `user-1` de los datos de ejemplo. Por eso el token del registro es hoy la forma fiable de
> empezar a trabajar.

### Sesión: login, logout y whoami

```bash
uv run activity-bookings auth login --email m@f.c   # iniciar sesión con una cuenta existente
uv run activity-bookings auth whoami                 # ver la sesión actual
uv run activity-bookings auth logout                 # cerrar la sesión local
```

- `auth login`: `--email` se pide de forma interactiva si se omite. La contraseña se pide siempre
  por un prompt oculto, sin confirmación; no existe opción `--password`. Un login correcto guarda
  la sesión en el mismo fichero que el registro (`session.json`, permisos `0600`) y sustituye la
  anterior; uno fallido la deja intacta.
- `auth logout`: borra el fichero de sesión local, aunque esté corrupto. Si no hay sesión, muestra
  `Not logged in.` y termina sin error. No llama a la API: la API no tiene endpoint de logout, así
  que el token no se invalida en el servidor y sigue siendo válido hasta que caduca (24 h).
- `auth whoami`: muestra el usuario, el email, el ID, la URL de la API y la caducidad del token,
  leídos de la sesión local sin consultar la API. La caducidad se lee del JWT sin verificar su
  firma; si ya ha pasado, se marca como `(expired)` y se sugiere volver a hacer login, y si no se
  puede leer se muestra `unknown`. Sin sesión, o con un fichero de sesión inválido, termina con
  `Error:` y código 1.

> **Fallo conocido del servidor** (punto 1 de «Discrepancias y dudas» en
> `docs/api-reference.md`): `auth login` responde `Invalid email or password` con los usuarios de
> los datos de ejemplo (p. ej. `m@f.c`), aunque la contraseña sea correcta (comprobado con la API en
> marcha), y probablemente también con los recién registrados. Es un fallo de la API, no de la CLI:
> trabaja con la sesión que deja `auth register`.

### Listado de actividades

```bash
uv run activity-bookings activities list                                 # todas las actividades
uv run activity-bookings activities list --search bike                   # búsqueda por texto
uv run activity-bookings activities list --sort price --order desc       # orden en el servidor
uv run activity-bookings activities list --status published              # solo las publicadas
```

- Por defecto muestra todas las actividades que devuelve la API, sea cual sea su estado, en una
  tabla con ID, nombre, fecha, lugar, precio, capacidad y estado. No necesita sesión: la ruta es
  pública y no se envía el token.
- `--search TEXT`: la API busca el texto, sin distinguir mayúsculas, en el nombre, el lugar y el
  slug. No puede estar vacío.
- `--sort {date,price,name,location}` y `--order {asc,desc}`: la API ordena el listado; `--order`
  vale `asc` por defecto y solo se puede usar junto con `--sort`.
- `--status {draft,published,confirmed,sold-out,done,cancelled}`: la API no filtra por estado,
  así que el filtro se aplica en el cliente sobre la lista recibida.
- La columna Capacity es la capacidad total (`maxParticipants`), no las plazas libres: la API no
  las expone.
- Si no hay resultados, muestra `No activities found.` y termina con código 0.

### Detalle de una actividad

```bash
uv run activity-bookings activities show activity-2
```

- `ACTIVITY_ID` (obligatorio, no puede estar vacío) es el ID que muestra `activities list`, p. ej.
  `activity-2`. No se puede buscar por slug ni por nombre.
- No necesita sesión: la ruta es pública y no se envía el token aunque haya una sesión guardada.
- Muestra una ficha con ID, Name, Slug, Date, Duration (en minutos), Location, Price, Min
  participants, Capacity, Status, Organizer (el `userId` del dueño; la API no da su nombre),
  Created y, si la actividad se ha modificado, Updated.
- Capacity es la capacidad total (`maxParticipants`), no las plazas libres: la API no las expone.
- Si la actividad no existe, muestra `Error: Activity not found` y termina con código 1.

### Gestión de mis actividades

```bash
uv run activity-bookings activities create --name Yoga --price 20 --date 2027-01-15 \
    --location Park --min-participants 2 --max-participants 10 [--duration 90]
uv run activity-bookings activities update activity-5 --price 25 --max-participants 12
uv run activity-bookings activities delete activity-5          # pide confirmación [y/N]
uv run activity-bookings activities delete activity-5 --yes    # sin confirmación (también -y)
```

- `create`: `--name`, `--price`, `--date`, `--location`, `--min-participants` y
  `--max-participants` son obligatorias; `--duration` (minutos) es opcional y la API usa 60 si no
  se indica. La actividad se crea en estado `draft` y a nombre del usuario de la sesión. Muestra
  la actividad creada.
- `update ACTIVITY_ID`: acepta las mismas opciones, todas opcionales, y envía solo las indicadas.
  Hay que indicar al menos una. Muestra la actividad actualizada. El estado no se puede cambiar
  con este comando: para eso está `activities status`.
- `delete ACTIVITY_ID`: pide confirmación (por defecto «no»); `--yes` / `-y` se la salta. Si no
  se confirma, muestra `Deletion cancelled.` y termina con código 0.
- `--date` acepta `YYYY-MM-DD` o ISO 8601 con hora; si lleva hora, indica también la zona
  (p. ej. `2027-01-15T10:00:00Z`), porque si no el servidor la interpreta en su zona horaria. La
  API exige que sea futura.
- Las reglas (fecha futura, precio positivo, mínimo ≤ máximo, ser el dueño de la actividad) las
  comprueba el servidor; la CLI muestra su mensaje y los campos con error, y termina con código 1.
- Los cuatro comandos (`create`, `update`, `delete` y `status`) necesitan sesión
  (`auth register` o `auth login`) y envían su token. Fallan sin llamar a la API, sugiriendo
  `auth login`, si no hay sesión, si el fichero de sesión no es válido, si la sesión es de otra
  URL de API distinta de la configurada o si el token ya ha caducado. Si el servidor rechaza el
  token (401), se muestra su mensaje y la misma sugerencia; el fichero de sesión no se borra.

> **Fallos conocidos del servidor** (puntos 1 y 7 de «Discrepancias y dudas» en
> `docs/api-reference.md`):
>
> - (1a) Como `auth login` falla con los usuarios de ejemplo, lo normal es trabajar
>   con la sesión de `auth register`. Ese usuario no es dueño de las actividades de ejemplo, así
>   que modificarlas, borrarlas o cambiarles el estado dará `You can only update/delete/transition
>   your own activities`: solo se pueden gestionar las actividades creadas con esa sesión.
> - (1b) El contador de IDs del servidor empieza en 1, así que un `activities create` podría
>   sobrescribir `activity-1` u otra actividad existente.
> - (7) El servidor no impide borrar una actividad con reservas. Después, `GET /bookings` y
>   `GET /bookings/:id` de esas reservas probablemente respondan con un error 500.

### Cambiar el estado de una actividad

```bash
uv run activity-bookings activities status activity-5 published         # publicar (se puede reservar)
uv run activity-bookings activities status activity-5 cancelled         # pide confirmación [y/N]
uv run activity-bookings activities status activity-5 done --yes        # sin confirmación (también -y)
```

- `ACTIVITY_ID` (no puede estar en blanco) y `NEW_STATUS`, uno de `draft`, `published`,
  `confirmed`, `sold-out`, `done` o `cancelled`, en minúsculas. Otro valor es error de uso
  (código 2) y no llama a la API.
- Muestra `Activity <id> is now <status>.` y la actividad devuelta, como `create` y `update`.
- Pasar a `cancelled` o `done` es definitivo y pide confirmación (por defecto «no»); `--yes` / `-y`
  se la salta. Si no se confirma, muestra `Status change cancelled.` y termina con código 0. Los
  demás estados se envían sin preguntar.
- Transiciones que admite la API (la CLI no las comprueba: si no es válida, muestra el mensaje de la
  API, que indica las posibles, y termina con código 1):

  | Desde | Hacia |
  |---|---|
  | `draft` | `published` |
  | `published` | `confirmed`, `cancelled`, `sold-out` |
  | `confirmed` | `done`, `cancelled` |
  | `sold-out` | `confirmed` |
  | `done`, `cancelled` | ninguno (estados finales) |

- Solo el dueño puede cambiar el estado (si no, `Error: You can only transition your own
  activities`). Una actividad recién creada está en `draft` y hay que publicarla para poder
  reservarla.
- Cancelar una actividad **no** cancela ni reembolsa sus reservas: la API solo cambia el estado.

### Reservar plazas

```bash
uv run activity-bookings bookings create activity-2              # 1 plaza, pide confirmación [y/N]
uv run activity-bookings bookings create activity-2 -p 2         # 2 plazas (también --participants)
uv run activity-bookings bookings create activity-2 -p 2 --yes   # sin confirmación (también -y)
```

- `ACTIVITY_ID` (obligatorio, no puede estar vacío) es el ID que muestra `activities list`.
- `--participants` / `-p`: número entero de plazas, 1 o más; por defecto, 1.
- Necesita sesión y aplica las mismas comprobaciones que la gestión de actividades (sin sesión,
  sesión de otra API o caducada: falla sin llamar a la API; 401: sugiere `auth login`).
- Antes de reservar consulta la actividad y solo sigue si está `published` y su fecha no ha
  pasado. Una fecha sin hora cuenta como no pasada durante todo ese día y las fechas se comparan
  en UTC, no en tu zona horaria. El servidor no hace esta comprobación.
- Sin `--yes` / `-y`, pide confirmación (por defecto «no») con la actividad, la fecha, las plazas y
  el total. Si no se confirma, muestra `Booking cancelled.` y termina con código 0.
- El total (precio × plazas) lo calcula la CLI: la API no devuelve el importe cobrado.
- **El cobro es inmediato y la reserva no se puede cancelar ni modificar**: la API no lo permite.
- Si va bien, muestra `Booking <id> created.` y una ficha con ID, Activity, Date, Participants,
  Total y Payment (el estado del pago).
- Los errores de la API se muestran como `Error: ...` con código 1, p. ej.
  `Capacity exceeded. Available: 13, Requested: 20`. La capacidad la comprueba el servidor.
- El pago rechazado (402, `Payment could not be processed`) solo ocurre cuando el importe es
  múltiplo de 1000; con los datos de ejemplo, en la práctica no se puede provocar.

### Mis reservas

```bash
uv run activity-bookings bookings list                         # todas mis reservas
uv run activity-bookings bookings list --activity activity-2   # solo las de una actividad
```

- `--activity ACTIVITY_ID`: la API devuelve solo las reservas de esa actividad (no puede estar
  vacío). Sin la opción, se listan todas.
- Necesita sesión, con las mismas comprobaciones que `bookings create`.
- Muestra la tabla `My bookings` en el orden que da la API, con ID, Activity (nombre e ID), Date,
  Seats, Total, Payment y Activity status, seguida del recuento (`N bookings` / `1 booking`). Sin
  reservas: `No bookings found.` con código 0.
- El **total** lo calcula la CLI con el precio **actual** de la actividad × plazas: la API no
  guarda el importe cobrado, así que si el precio cambió después de reservar no coincidirá.
- La API no tiene un estado propio de la reserva: se muestra el estado del pago (`Payment`; si falta,
  `pending`) y el de la actividad (`Activity status`) por separado.
- Si alguna reserva apunta a una actividad borrada, la API responde 500
  (`Failed to retrieve bookings`) para **todo** el listado; la CLI muestra el error con esa causa
  probable y termina con código 1. Los demás errores también salen como `Error: ...` con código 1.

### Detalle de una reserva

```bash
uv run activity-bookings bookings show booking-1
```

- `BOOKING_ID` (obligatorio, no puede estar en blanco): ID de una reserva propia, p. ej. el que
  muestra `bookings list`. Un ID vacío es error de uso (código 2) y no llama a la API.
- Necesita sesión, con las mismas comprobaciones que `bookings create`.
- Muestra una ficha con ID, Activity (nombre e ID), Date, Duration, Location, Seats, Price (por
  plaza), Total, Payment, Payment ID (solo si la reserva tiene pago asociado), Activity status y
  Booked at (fecha de la reserva).
- Como en el listado, el **total** usa el precio **actual** de la actividad × plazas, no el
  importe cobrado.
- `Error: Booking not found` (código 1) tanto si la reserva no existe como si es de otro usuario:
  la API no distingue ambos casos.
- Si la actividad de la reserva se ha borrado, la API responde 500 (`Failed to retrieve booking`);
  la CLI muestra el error con esa causa probable y termina con código 1. Los demás errores también
  salen como `Error: ...` con código 1.

### Configuración

La URL de la API se lee de `$XDG_CONFIG_HOME/activity-bookings/config.toml`
(por defecto `~/.config/activity-bookings/config.toml`). Si el fichero no existe o no define
`api_url`, se usa `http://localhost:3000`.

```toml
api_url = "http://localhost:3000"
```

### Calidad

```bash
uv run ruff check
uv run ruff format --check
uv run mypy src tests
uv run pytest
```

---

- **Author**: [Alberto Basalo](https://albertobasalo.dev)
- **Ai Code Academy en Español**: [AI code Academy](https://aicode.academy)
- **Socials**:
  - [X](https://x.com/albertobasalo)
  - [LinkedIn](https://www.linkedin.com/in/albertobasalo/)
  - [GitHub](https://github.com/albertobasalo)


