# Proposal

## Why

Cada acción de la CLI exige recordar el subcomando y sus opciones, lo que la hace incómoda en las
sesiones de formación y demos. Un menú navegable con flechas permite listar, consultar, crear y
reservar sin memorizar la sintaxis, reutilizando los subcomandos que ya existen.

## What Changes

- `activity-bookings` sin subcomando y en un terminal interactivo abre un menú navegable con
  flechas y Enter. Sin terminal interactivo (scripts, tuberías) sigue mostrando la ayuda, como hoy.
- El menú agrupa las acciones existentes: actividades (listar, ver, crear, modificar, borrar,
  cambiar estado), reservas (reservar, mis reservas, ver reserva), cuenta (registro, login, logout,
  whoami), configuración y «Exit».
- Cada opción pide sus datos con prompts y ejecuta el subcomando correspondiente: la validación, la
  sesión, los errores y la salida son los del subcomando. Tras cada acción, también tras un error,
  vuelve al menú. «Exit», Esc o Ctrl+C terminan con código 0.
- La cabecera del menú indica si hay sesión y de qué usuario. `--config` se respeta.
- **Nueva dependencia:** `questionary`, para la selección con flechas (justificada en el design).

## Capabilities

### New Capabilities

- `interactive-menu`: menú interactivo que da acceso a los subcomandos de la CLI.

### Modified Capabilities

- `cli-shell`: la invocación sin argumentos muestra la ayuda solo sin terminal interactivo; con
  terminal abre el menú.

## Fuera de alcance

- Elegir la actividad o la reserva de una lista cargada de la API: se pide el ID.
- Cambiar el comportamiento, las opciones o la salida de cualquier subcomando.
- Prompts interactivos dentro de los subcomandos cuando faltan opciones.
- Personalizar el menú, atajos de teclado o historial.

## Impact

- **Requisitos previos:** todos los subcomandos actuales, hasta `add-activity-status`.
- **Código:** `cli.py` (arranque sin subcomando) y un módulo nuevo `interactive.py`.
- **Dependencias:** `questionary` (con `uv add`).
- **Tests:** nuevos, con prompts simulados y respx; el de la ayuda sin argumentos se mantiene.
- **Documentación:** README (modo interactivo) y AGENTS.md (stack y layout).
