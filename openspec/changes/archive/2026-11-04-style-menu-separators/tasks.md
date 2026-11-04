# Tasks

## 1. Estilo de los separadores (interactive-menu)

- [x] 1.1 Añadir `MENU_STYLE` (clase `separator` en `fg:ansibrightblack`) en `interactive.py` y pasarlo a `questionary.select` en `QuestionaryPrompter.select`; test en `tests/test_interactive.py` con `questionary.select` sustituido por un doble (recibe el estilo, las secciones como `Separator` con su texto, las opciones como `Choice`, y devuelve el valor elegido), pasando; los tests existentes siguen pasando sin cambios
- [x] 1.2 Añadir al README, en «Modo interactivo», que los títulos de sección se muestran atenuados y no se pueden seleccionar

## 2. Verificación final

- [x] 2.1 Revisar el menú en un terminal real (`uv run activity-bookings`): los títulos de sección salen en gris y las opciones como antes; anotar el resultado. Comprobado con una pseudoterminal (pty, `TERM=xterm-256color`): los cuatro títulos se emiten con SGR `0;90` (gris ANSI) y las opciones con `0` (sin color). Queda pendiente el vistazo de una persona
- [x] 2.2 Ejecutar `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` y verificar que todo pasa

## Workflow follow-up

- Revisar el change con el subagente `spec-reviewer` antes de archivar.
- Archivar con `/opsx:archive` cuando la verificación completa pase.
