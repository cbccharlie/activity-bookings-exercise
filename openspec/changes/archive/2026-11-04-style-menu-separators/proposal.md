# Proposal

## Why

En el menú interactivo, los títulos de sección (`── Activities ──`, `── Bookings ──`...) se ven con
el mismo color y sangría que las opciones, y pueden confundirse con algo que se puede elegir. Se
detectó en la revisión visual del menú tras `add-interactive-menu`.

## What Changes

- Los títulos de sección del menú se muestran atenuados (gris del tema del terminal), distintos de
  las opciones, que mantienen el aspecto actual.
- Nada más cambia: mismas opciones, mismo orden, mismo texto de los títulos y misma navegación (el
  cursor sigue saltándose los títulos).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `interactive-menu`: el requisito «Menú principal» exige que los títulos de sección se distingan
  visualmente de las opciones.

## Fuera de alcance

- Cambiar los colores de las opciones, del cursor, de la pregunta o de los demás prompts.
- Quitar los separadores o cambiar su texto, o reorganizar el menú.
- Temas configurables por el usuario.
- Los prompts de Typer que aparecen dentro del menú (contraseñas, confirmación de la reserva).

## Impact

- **Requisitos previos:** `add-interactive-menu`.
- **Código:** `interactive.py` (`QuestionaryPrompter.select` pasa un estilo a `questionary`).
- **Tests:** uno nuevo para el estilo del separador. **Dependencias:** ninguna.
- **Documentación:** README (una línea en «Modo interactivo»).
