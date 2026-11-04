# Design

## Context

`QuestionaryPrompter.select` (`src/activity_bookings/interactive.py`) convierte cada `Section` en un
`questionary.Separator("── <título> ──")` y llama a `questionary.select(message, choices=...)` sin
estilo. `questionary` pinta los separadores con la clase de estilo `separator`, que en su estilo por
defecto está vacía (`questionary/constants.py`, `("separator", "")`): por eso salen igual que las
opciones. Los separadores ya no son seleccionables (`is_selection_a_separator`).

Ver proposal.md para la motivación.

## Goals / Non-Goals

**Goals:**
- Los títulos de sección se ven atenuados y el resto del menú queda igual.

**Non-Goals:**
- Un tema propio para todos los prompts.
- Cambiar `Prompter`, `run_menu` o el `FakePrompter` de los tests: el estilo es asunto solo de la
  implementación con `questionary`.

## Decisions

### Estilo

```python
MENU_STYLE = questionary.Style([("separator", "fg:ansibrightblack")])
...
questionary.select(message, choices=choices, style=MENU_STYLE).ask()
```

- `fg:ansibrightblack` es el «gris» de la paleta ANSI del terminal: se adapta al tema del usuario
  (claro u oscuro) en lugar de fijar un color RGB que podría no leerse en algún fondo.
- Solo se define la clase `separator`: `questionary` combina el estilo pasado con el suyo por
  defecto, así que las opciones, el cursor y la pregunta conservan su aspecto actual.

*Alternativas descartadas:*
- Color RGB fijo (p. ej. `#888888`): peor contraste en terminales con fondo claro.
- `italic` o `bold`: no todos los terminales los muestran; el color basta para distinguirlos.
- Quitar los separadores y prefijar el grupo en cada opción: cambia el texto del menú y los tests
  existentes, y el usuario eligió el estilo propio.

### Presentación

Igual que ahora, con las líneas de sección en gris:

```console
Logged in as tonto
? What do you want to do? (Use arrow keys)
   ── Activities ──          ← gris
 » List activities
   Show an activity
   ...
   ── Bookings ──            ← gris
   Book an activity
   ...
```

### Dependencias

Ninguna nueva (`questionary.Style` viene de `prompt_toolkit`, que ya está instalado).

### Tests

- `tests/test_interactive.py`: test unitario de `QuestionaryPrompter.select` con `monkeypatch` de
  `questionary.select` por un doble que registra sus argumentos y devuelve un objeto con `.ask()`.
  Comprueba que recibe `style` con la clase `separator` en `fg:ansibrightblack`, que las secciones
  llegan como `questionary.Separator` con su texto y las opciones como `questionary.Choice`, y que se
  devuelve el valor elegido. No hace falta un terminal.
- El aspecto real se revisa a mano en un terminal (tarea de prueba manual).

## Risks / Trade-offs

- [En algún tema, `ansibrightblack` puede quedar muy tenue] → Es el gris estándar de la paleta del
  terminal; si molesta, cambiarlo es una línea.
- [El test comprueba la configuración, no los píxeles] → Se complementa con la revisión visual.
