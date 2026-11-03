# Tasks

## 1. Andamiaje del proyecto con uv

- [x] 1.1 Verificar que uv está instalado (`uv --version`); si no, instalarlo con el instalador oficial y comprobar que `uv --version` responde
- [x] 1.2 Crear el proyecto con `uv init --package` (paquete `activity_bookings`, distribución `activity-bookings`, layout `src/`, backend `uv_build`, versión `0.1.0`, `requires-python = ">=3.12"`) y verificar que existen `pyproject.toml` y `src/activity_bookings/__init__.py`
- [x] 1.3 Añadir dependencias `typer` y `rich` (`uv add`) y el grupo dev `pytest`, `ruff`, `mypy` (`uv add --dev`), y verificar que `uv sync` termina sin errores y genera `uv.lock`
- [x] 1.4 Configurar ruff (py312, line-length 100, reglas `E,F,I,UP,B,SIM,RUF`), mypy (`strict = true`) y pytest (`testpaths = ["tests"]`) en `pyproject.toml`, y verificar que `uv run ruff check` y `uv run mypy src` se ejecutan sin errores sobre el paquete vacío
- [x] 1.5 Crear `.gitignore` para Python/uv (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `.idea/`) y verificar con `git status` que no aparecen ficheros generados

## 2. Comando `activity-bookings` (cli-shell)

- [x] 2.1 Crear `tests/conftest.py` con una fixture `CliRunner` y una fixture autouse que fije `HOME` y `XDG_CONFIG_HOME` dentro de `tmp_path`, y verificar que `uv run pytest` arranca (sin tests todavía)
- [x] 2.2 Implementar `__version__` con `importlib.metadata`, `console.py` (stdout/stderr Rich) y `cli.py` con app Typer raíz (`no_args_is_help=True`, `pretty_exceptions` desactivado), opción eager `--version` y `main()`; añadir `[project.scripts] activity-bookings = "activity_bookings.cli:main"`; tests de `--help`, `--version` y sin argumentos en `tests/test_cli.py` pasando
- [x] 2.3 Añadir `__main__.py` y un test `subprocess` de `python -m activity_bookings --help` (código 0, misma ayuda), y verificar que pasa
- [x] 2.4 Añadir tests de subcomando y opción desconocidos que comprueben el código de salida 2 y el mensaje de error, y verificar que pasan
- [x] 2.5 Implementar `errors.py` (`ActivityBookingsError`, `ConfigError`) y el helper `handle_errors`, que imprime `Error: <mensaje>` por stderr y sale con 1; test con un comando de prueba que lanza `ActivityBookingsError` y comprueba el mensaje, el código 1 y la ausencia de `Traceback`

## 3. Configuración del cliente (client-config)

- [x] 3.1 Implementar `Settings` (dataclass frozen) y `default_config_path()` respetando `XDG_CONFIG_HOME`; tests en `tests/test_config.py` para la ruta por defecto con y sin `XDG_CONFIG_HOME` pasando
- [x] 3.2 Implementar `load_settings(path)` con `tomllib` para el caso de fichero válido, fichero inexistente (valor por defecto `http://localhost:3000`), clave `api_url` ausente y claves desconocidas ignoradas; tests de cada caso pasando
- [x] 3.3 Añadir la validación (TOML mal formado, `api_url` no texto, esquema distinto de http/https o sin host, ruta de `--config` inexistente) lanzando `ConfigError` con la ruta y la causa, y la normalización de la barra final; tests de cada escenario de error y de normalización pasando
- [x] 3.4 Añadir la opción global `--config PATH` en el callback raíz (guardada en `ctx.obj`, carga perezosa) e implementar `commands/config_cmd.py` con el subcomando `config` (URL y origen en una tabla Rich, con `handle_errors`); tests CLI de los escenarios de `client-config` (por defecto, XDG, `--config`, inexistente, inválido) pasando
- [x] 3.5 Comprobar que `activity-bookings --help` y `--version` funcionan aunque el fichero de configuración sea inválido, con un test que lo cubra

## 4. Documentación

- [x] 4.1 Añadir al README una sección «ActivityBookings CLI» con requisitos (Python 3.12+, uv), instalación (`uv sync`), uso (`uv run activity-bookings --help`, `config`), formato y ubicación de `config.toml`, y comandos de calidad; verificar que los comandos documentados funcionan tal como están escritos

## 5. Verificación final

- [x] 5.1 Ejecutar `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests` y `uv run pytest`, y verificar que todos terminan sin errores
