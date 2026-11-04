# Design

## Context

Hoy `cli.py` crea el `Typer` raíz con `no_args_is_help=True`: sin argumentos muestra la ayuda y
termina con código 2 (comportamiento de Typer). Cada subcomando ya resuelve por su cuenta la
validación (Typer), la sesión (`commands/_auth.py`), los errores (`errors.handle_errors`) y la
salida (consolas de `console.py`). Varios piden datos con `typer.prompt`/`typer.confirm`
(contraseñas en `auth`, confirmación con el total en `bookings create`).

Comprobado antes de proponer:
- `typer.main.get_command(app).main(args, prog_name=...)` ejecuta un subcomando completo y termina
  siempre con `SystemExit` (0, 1 o 2), también ante errores de uso. Capturándolo, un bucle puede
  invocar varios subcomandos seguidos.
- Dentro de `CliRunner`, esas invocaciones anidadas escriben en la salida capturada: el menú se puede
  testear de punta a punta como cualquier comando.
- `questionary` 2.1.1 trae `py.typed` y solo depende de `prompt_toolkit` (>=2,<4).

El comportamiento exigido está en `specs/interactive-menu/spec.md` y `specs/cli-shell/spec.md`.

## Goals / Non-Goals

**Goals:**
- El menú solo recoge datos y monta argumentos; toda la lógica sigue en los subcomandos.
- Ningún subcomando cambia de comportamiento.
- Tests deterministas sin terminal real.

**Non-Goals:**
- Pantalla completa (TUI) o refresco de la pantalla entre acciones.
- Validar los datos en el menú antes de ejecutar (lo hace el subcomando, con sus mensajes).

## Decisions

### Estructura

```
src/activity_bookings/
  cli.py           # invoke_without_command, _is_interactive(), _executor(), _make_prompter()
  interactive.py   # nuevo: Prompter, QuestionaryPrompter, run_menu() y una función por opción
tests/
  test_interactive.py   # nuevo
  test_cli.py           # ayuda sin TTY y apertura del menú con TTY
```

### Dependencia: `questionary`

Necesaria para la selección con flechas y Enter: Rich y Typer solo ofrecen prompts de texto. Es la
librería más extendida para esto, tipada (`py.typed`) y con una sola dependencia
(`prompt_toolkit`). Se añade con `uv add questionary`.

*Alternativas descartadas:*
- Menú numerado con `rich.prompt`: sin dependencia, pero no es lo pedido (flechas).
- `InquirerPy` / `simple-term-menu`: menos mantenidas o sin soporte de Windows.
- `textual`: una TUI completa, desproporcionada para «pocos cambios».

### Arranque (`cli.py`)

- El `Typer` raíz pasa a `invoke_without_command=True` (se quita `no_args_is_help`).
- En `root()`, si `ctx.invoked_subcommand is None`:
  - `_is_interactive()` (`sys.stdin.isatty() and sys.stdout.isatty()`) → `run_menu(...)`.
  - Si no → `typer.echo(ctx.get_help(), nl=False)` y `typer.Exit(code=2)`, para conservar el
    resultado actual en scripts. Con la ayuda Rich, Typer la imprime él mismo y `get_help()`
    devuelve `""`, así que la salida es la de antes.
- `_executor(config)` devuelve la función `execute(args)` que usa el menú: antepone
  `["--config", <ruta>]` si se pasó y llama a
  `typer.main.get_command(app).main(args, prog_name="activity-bookings")` dentro de
  `contextlib.suppress(SystemExit)`. Vive en `cli.py` porque necesita `app`; `interactive.py` la
  recibe como parámetro y así no importa `cli.py` (evita el import circular).
- `_make_prompter()` devuelve `QuestionaryPrompter()`; los tests lo sustituyen con `monkeypatch`.

### Prompts (`interactive.py`)

```python
class Prompter(Protocol):
    def select(self, message: str, items: Sequence[MenuItem]) -> str | None: ...
    def text(self, message: str, default: str = "") -> str | None: ...
    def confirm(self, message: str) -> bool | None: ...
```

- `QuestionaryPrompter` usa `questionary.select/text/confirm(...).ask()`, que devuelve `None` si el
  usuario cancela (Esc o Ctrl+C). `MenuItem` es un `Choice` (etiqueta y valor) o un `Section`
  (título de sección, que se muestra como `questionary.Separator`).
- En los tests, un `FakePrompter` responde con una lista de respuestas guionizadas y falla si se le
  pregunta más de lo previsto.
- `run_menu(prompter, execute)`: bucle que imprime la cabecera de sesión, pide la opción y llama a
  su función; `None` o `Exit` termina. Cada función de opción pide sus datos; si alguno es `None`
  vuelve al menú sin ejecutar nada.

### Cabecera de sesión

`load_session()` (`session.py`): `Logged in as <username>` o `Not logged in`. Si el fichero está
dañado (`SessionError`) también `Not logged in`; el error real saldrá al ejecutar una acción
protegida. No llama a la API ni comprueba la caducidad.

### Opciones → argumentos

| Opción | Argumentos montados |
|---|---|
| List activities | `activities list` + `--search T` si no vacío + `--status S` si no es «any» |
| Show an activity | `activities show ID` |
| Create an activity | `activities create --name N --price P --date D --location L --min-participants A --max-participants B` + `--duration M` si no vacío |
| Update an activity | `activities update ID` + cada `--campo valor` no vacío |
| Delete an activity | `confirm` → `activities delete ID --yes` |
| Change an activity's status | `select` de `ActivityStatus`; `confirm` si está en `FINAL_STATUSES` → `activities status ID S --yes` |
| Book an activity | `bookings create ID --participants N` (por defecto `1`; el comando pide su confirmación) |
| My bookings | `bookings list` + `--activity ID` si no vacío |
| Show a booking | `bookings show ID` |
| Register | `auth register --username U --email E` (el comando pide contraseña y términos) |
| Log in | `auth login --email E` (el comando pide la contraseña) |
| Log out / Who am I / Show configuration | `auth logout` / `auth whoami` / `config` |

- Los números se pasan como texto: la validación y su error (`Invalid value for '--price'`) son los
  de Typer, con código 2, y el menú sigue.
- `delete` y `status` se confirman con `questionary` y llevan `--yes`, para no mezclar estilos. En
  `bookings create` se deja la confirmación del comando porque muestra el total calculado con la
  actividad.
- Se reutilizan `ActivityStatus` y `FINAL_STATUSES` de `commands/activities_cmd.py`.

### Presentación

```console
$ activity-bookings
Logged in as Ana
? What do you want to do? (Use arrow keys)
   ── Activities ──
 » List activities
   Show an activity
   Create an activity
   Update an activity
   Delete an activity
   Change an activity's status
   ── Bookings ──
   Book an activity
   My bookings
   Show a booking
   ── Account ──
   Register
   Log in
   Log out
   Who am I
   ── Settings ──
   Show configuration
   Exit

? What do you want to do? Change an activity's status
? Activity ID: activity-5
? New status: cancelled
? Change activity activity-5 to cancelled? This cannot be undone. (y/N) y
Activity activity-5 is now cancelled.
ID        activity-5
...
Logged in as Ana
? What do you want to do? (Use arrow keys)

$ activity-bookings | cat          # sin terminal: la ayuda, como hoy
Usage: activity-bookings [OPTIONS] COMMAND [ARGS]...
```

### Tests

- `tests/test_interactive.py`: un test por escenario de `interactive-menu`, con `CliRunner` y
  `respx_mock`. Un fixture `menu(answers)` hace `monkeypatch` de `cli._is_interactive` (→ `True`) y de
  `cli._make_prompter` (→ `FakePrompter(answers)`), e invoca `app` sin argumentos. «El menú se vuelve
  a mostrar» se comprueba contando la cabecera de sesión o las llamadas a `select`.
- `tests/test_cli.py`: el test actual de la ayuda sin argumentos sigue igual (CliRunner no es TTY);
  se añaden el de apertura del menú con TTY y el de un subcomando con TTY que no lo abre.
- `QuestionaryPrompter` no se testea (es una capa fina sobre la librería); se excluye de la cobertura
  implícitamente y se prueba a mano.

## Risks / Trade-offs

- [Dependencia nueva] → Acotada a `QuestionaryPrompter`; cambiarla solo toca esa clase.
- [En el menú se mezclan prompts de `questionary` y de Typer (contraseñas, confirmación de la
  reserva)] → Funcionan en la misma terminal; la diferencia es solo visual.
- [Los errores de uso de Typer muestran una línea `Usage: activity-bookings ...` que no aplica al
  menú] → Se acepta: el mensaje del error sigue siendo claro y el menú continúa.
- [`invoke_without_command` cambia cómo se procesa la invocación sin argumentos] → El test de ayuda
  existente y el nuevo escenario sin TTY protegen el comportamiento actual, incluido el código 2.
- [Terminales sin soporte de `prompt_toolkit` (p. ej. algunos IDE)] → Sin TTY se muestra la ayuda; los
  subcomandos siguen funcionando igual.
