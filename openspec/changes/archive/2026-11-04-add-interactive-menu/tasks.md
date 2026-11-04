# Tasks

## 1. Preparación

- [x] 1.1 Comprobar que existen todos los subcomandos que usa el menú (`activities list/show/create/update/delete/status`, `bookings create/list/show`, `auth register/login/logout/whoami`, `config`), `ActivityStatus` y `FINAL_STATUSES` en `activities_cmd.py`, `load_session()` y `SessionError`, y que `uv run pytest` pasa. Si no, detenerse y avisar
- [x] 1.2 Añadir la dependencia con `uv add questionary` (sin editar `uv.lock` a mano) y verificar que `uv run mypy src tests` sigue pasando con ella instalada

## 2. Arranque y esqueleto del menú (cli-shell, interactive-menu)

- [x] 2.1 Crear `interactive.py` con el protocolo `Prompter`, `QuestionaryPrompter`, la cabecera de sesión y `run_menu(prompter, execute)` con el menú completo de opciones y separadores, `Exit` y cancelación (`None`), todavía sin acciones; en `cli.py`, pasar a `invoke_without_command=True` con `_is_interactive()`, `_execute()` (con `--config`) y `_make_prompter()`; crear en `tests/test_interactive.py` el `FakePrompter` y el fixture `menu(answers)`; tests de «Menú principal» (opciones y orden), «Indicación de la sesión» (sin sesión, con sesión, fichero dañado) y «Navegación y salida» (Exit, cancelar), y en `tests/test_cli.py` de cli-shell (sin TTY → ayuda con código 2 como hoy, con TTY → menú, subcomando con TTY → no abre el menú), pasando

## 3. Acciones del menú (interactive-menu)

- [x] 3.1 Implementar `List activities` y `Show an activity`; tests de «Consulta de actividades» (filtros `bike` y `published`; ver `activity-2`) y de «Vuelta al menú tras una acción», pasando
- [x] 3.2 Implementar `Create an activity` y `Update an activity` (datos opcionales vacíos omitidos, cancelación de un prompt → vuelta al menú); tests de «Alta y modificación de actividades» (crear sin duración, modificar solo el precio) y de «Abandonar una acción a medias», pasando
- [x] 3.3 Implementar `Delete an activity` y `Change an activity's status` con `confirm` de `questionary` y `--yes`; tests de «Borrado y cambio de estado desde el menú» (borrado confirmado y rechazado, publicar sin confirmación, cancelación rechazada), pasando
- [x] 3.4 Implementar `Book an activity`, `My bookings`, `Show a booking`, `Register`, `Log in`, `Log out`, `Who am I` y `Show configuration`; tests de «Acciones sobre reservas, cuenta y configuración» (ver reserva, mis reservas sin filtro, reservar 2 plazas confirmando en el prompt del comando, cerrar sesión, ver configuración), pasando
- [x] 3.5 Añadir los tests de «Errores dentro del menú» (404 de la API, precio `abc`, acción protegida sin sesión, API caída; en todos vuelve al menú y termina con código 0 sin `Traceback`) y de «Configuración en el menú» (`--config custom.toml` usa su `api_url`), pasando

## 4. Documentación

- [x] 4.1 Documentar el modo interactivo en el README (cómo se abre, que sin terminal se muestra la ayuda, opciones, Esc/Ctrl+C, `--config`) y actualizar AGENTS.md (stack: `questionary`; layout: `interactive.py` y `tests/test_interactive.py`)
- [x] 4.2 Probar `uv run activity-bookings` en un terminal real: navegar con flechas, listar, ver una actividad, una acción con error y salir; anotar cualquier diferencia con la spec. Hecho con una pseudoterminal (pty) y pulsaciones reales contra la API local (solo GET): listado de 3 actividades, `activity-99` → `Error: Activity not found` y vuelta al menú, Ctrl+C → salida con código 0 (questionary muestra «Cancelled by user»). Sin diferencias con la spec. Queda pendiente una revisión visual por una persona

## 5. Verificación final

- [x] 5.1 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
