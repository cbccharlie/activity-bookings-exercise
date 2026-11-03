# Design

## Context

El repositorio solo contiene documentación (README, briefing) y la configuración de OpenSpec, sin código Python. El entorno de desarrollo tiene Python 3.12.3; uv aún no está instalado y es requisito previo. Motivación y alcance en `proposal.md`; comportamiento exigido en `specs/cli-shell` y `specs/client-config`.

## Goals / Non-Goals

**Goals:**
- Estructura de paquete que permita añadir comandos nuevos (cuenta, actividades, reservas) creando un módulo y registrándolo, sin tocar el resto.
- Configuración y manejo de errores centralizados, para que los comandos futuros los reutilicen.
- Tooling (ruff, mypy strict, pytest) pasando desde el primer commit.

**Non-Goals:**
- Diseñar la capa de cliente HTTP ni los modelos de dominio (actividad, reserva, usuario): se diseñarán con el primer change funcional.
- Logging, modo verbose, colores configurables o i18n.

## Decisions

### Estructura del proyecto

```
pyproject.toml
src/activity_bookings/
  __init__.py      # __version__ vía importlib.metadata
  __main__.py      # permite python -m activity_bookings
  cli.py           # app Typer raíz: callback global (--version, --config), registro de subcomandos, main()
  config.py        # Settings + load_settings() + default_config_path()
  errors.py        # ActivityBookingsError (base) y ConfigError
  console.py       # instancias Rich Console (stdout) y err_console (stderr)
  commands/
    __init__.py
    config_cmd.py  # subcomando `config`
tests/
  conftest.py      # fixtures: CliRunner, entorno aislado (HOME, XDG_CONFIG_HOME en tmp_path)
  test_cli.py
  test_config.py
```

- **Layout `src/`** (exigido por el proyecto): evita importar el paquete sin instalar y obliga a que los tests usen el paquete instalado.
- **Un módulo por grupo de comandos** en `commands/`: los futuros `auth.py`, `activities.py` y `bookings.py` se registran en `cli.py` con `app.add_typer(...)` o `app.command()`.

### Build y gestión con uv

`uv init --package` con backend `uv_build`, entry point `[project.scripts] activity-bookings = "activity_bookings.cli:main"`. Dependencias de desarrollo en `[dependency-groups] dev` (`pytest`, `ruff`, `mypy`). Configuración de ruff, mypy y pytest dentro de `pyproject.toml` para tener un único fichero. *Alternativa:* hatchling, igual de válido pero añade una herramienta más sin beneficio aquí.

### Versión

`__version__` se obtiene con `importlib.metadata.version("activity-bookings")`, de forma que la única fuente de verdad sea `pyproject.toml` (versión inicial `0.1.0`). `--version` es una opción *eager* del callback raíz de Typer, que imprime `activity-bookings 0.1.0` y sale con código 0.

### Configuración

- `tomllib` (stdlib): solo se necesita leer TOML, así que no hace falta ninguna dependencia nueva.
- `Settings` es una `dataclass(frozen=True)` con `api_url: str` y `source: Path | None` (`None` = valor por defecto). *Alternativa:* pydantic-settings. Se descarta porque para una sola clave añade una dependencia pesada; se puede reconsiderar si la configuración crece.
- `load_settings(path: Path | None)`: si `path` es `None` usa `default_config_path()` y tolera que no exista; si se pasa explícitamente (`--config`) y no existe, lanza `ConfigError`. Valida con `urllib.parse.urlsplit` (esquema http/https y host) y normaliza con `rstrip("/")`.
- **Carga perezosa:** el callback raíz solo guarda la ruta de `--config` en `ctx.obj`, y cada comando que necesite configuración llama a `load_settings`. Así `--help` y `--version` funcionan aunque el fichero esté roto.

Formato del fichero:

```toml
# ~/.config/activity-bookings/config.toml
api_url = "http://localhost:3000"
```

### Manejo de errores y códigos de salida

- Las excepciones de dominio heredan de `ActivityBookingsError`.
- `main()` envuelve `app()` (en modo `standalone_mode` de Typer/Click), captura `ActivityBookingsError` e imprime `Error: <mensaje>` en rojo por `err_console`, con `sys.exit(1)`.
- Los errores de uso los gestiona Click (código 2).
- La traza de Python solo aparece para fallos inesperados. Se desactiva `pretty_exceptions` de Typer para no mostrar variables locales.
- Para que los tests con `CliRunner` también cubran esta ruta, la captura se hace en un decorador o función auxiliar `handle_errors` aplicado a los comandos, en vez de solo en `main()`. Eso garantiza el mismo comportamiento invocando `app` directamente.

### Comandos y salida esperada

```console
$ activity-bookings --help
 Usage: activity-bookings [OPTIONS] COMMAND [ARGS]...

 ActivityBookings command line client.

╭─ Options ──────────────────────────────────────────────╮
│ --version            Show the version and exit.        │
│ --config       PATH  Path to the configuration file.   │
│ --help               Show this message and exit.       │
╰────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────╮
│ config   Show the effective configuration.             │
╰────────────────────────────────────────────────────────╯

$ activity-bookings --version
activity-bookings 0.1.0

$ activity-bookings config
API URL  http://localhost:3000
Source   default (no config file found at /home/user/.config/activity-bookings/config.toml)

$ activity-bookings --config ./custom.toml config
API URL  http://custom.example.com
Source   ./custom.toml

$ activity-bookings config        # con api_url = "ftp://example.com"
Error: invalid api_url 'ftp://example.com' in /home/user/.config/activity-bookings/config.toml: must be an http(s) URL with a host
$ echo $?
1
```

`activity-bookings` sin argumentos usa `no_args_is_help=True`. El código de salida en ese caso depende de la versión de Click y la spec no lo fija a propósito.

### Tests

- `typer.testing.CliRunner` para los escenarios de la CLI. Los tests de `config.py` llaman directamente a `load_settings`.
- Fixture autouse que fija `HOME` y `XDG_CONFIG_HOME` dentro de `tmp_path` mediante `monkeypatch`, para no leer nunca la configuración real del desarrollador.
- El escenario `python -m activity_bookings` se cubre con un test `subprocess` usando `sys.executable`.
- respx no se añade todavía, porque en este change no hay HTTP.

### Calidad

- ruff: `target-version = "py312"`, `line-length = 100`, reglas `E, F, I, UP, B, SIM, RUF`. Formateo con `ruff format`.
- mypy: `strict = true` sobre `src` y `tests`.

## Risks / Trade-offs

- [uv no instalado en la máquina] → Primera tarea: verificar o instalar uv y documentarlo en el README.
- [Cambios de comportamiento entre versiones de Typer/Click, p. ej. el código de salida de `no_args_is_help`] → Los tests comprueban solo lo que fija la spec; las versiones quedan fijadas en `uv.lock`.
- [`XDG_CONFIG_HOME` no es habitual en Windows] → Se acepta: el valor por defecto `~/.config` funciona en todas las plataformas y `--config` permite cualquier ruta.
- [Rich puede envolver líneas o añadir códigos ANSI que rompan aserciones en los tests] → Los tests comprueban subcadenas, y la consola Rich detecta que no hay TTY y desactiva colores con `CliRunner`.
