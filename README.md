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


