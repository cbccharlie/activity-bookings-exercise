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


