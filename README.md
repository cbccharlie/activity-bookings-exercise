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
> `docs/api-reference.md`): `auth login` probablemente responda `Invalid email or password` tanto
> con los usuarios de los datos de ejemplo (p. ej. `m@f.c`) como con los recién registrados. Si te
> ocurre, trabaja con la sesión que deja `auth register`.

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
  con este comando.
- `delete ACTIVITY_ID`: pide confirmación (por defecto «no»); `--yes` / `-y` se la salta. Si no
  se confirma, muestra `Deletion cancelled.` y termina con código 0.
- `--date` acepta `YYYY-MM-DD` o ISO 8601 con hora; si lleva hora, indica también la zona
  (p. ej. `2027-01-15T10:00:00Z`), porque si no el servidor la interpreta en su zona horaria. La
  API exige que sea futura.
- Las reglas (fecha futura, precio positivo, mínimo ≤ máximo, ser el dueño de la actividad) las
  comprueba el servidor; la CLI muestra su mensaje y los campos con error, y termina con código 1.
- Los tres comandos necesitan sesión (`auth register` o `auth login`) y envían su token. Fallan
  sin llamar a la API, sugiriendo `auth login`, si no hay sesión, si el fichero de sesión no es
  válido, si la sesión es de otra URL de API distinta de la configurada o si el token ya ha
  caducado. Si el servidor rechaza el token (401), se muestra su mensaje y la misma sugerencia; el
  fichero de sesión no se borra.

> **Fallos conocidos del servidor** (puntos 1 y 7 de «Discrepancias y dudas» en
> `docs/api-reference.md`):
>
> - (1a) Como `auth login` probablemente falle con los usuarios de ejemplo, lo normal es trabajar
>   con la sesión de `auth register`. Ese usuario no es dueño de las actividades de ejemplo, así
>   que modificarlas o borrarlas dará `You can only update/delete your own activities`.
> - (1b) El contador de IDs del servidor empieza en 1, así que un `activities create` podría
>   sobrescribir `activity-1` u otra actividad existente.
> - (7) El servidor no impide borrar una actividad con reservas. Después, `GET /bookings` y
>   `GET /bookings/:id` de esas reservas probablemente respondan con un error 500.

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


