# Design

## Context

No existen `AGENTS.md` ni `CLAUDE.md`. El código aún no está implementado: el stack, la estructura y los comandos salen de `openspec/changes/add-app-skeleton/design.md` y de `openspec/config.yaml`. Motivación en `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Un único fichero de instrucciones, corto y accionable, válido para cualquier agente.
- Que Claude Code lo cargue automáticamente sin duplicar contenido.

**Non-Goals:**
- Sustituir al README (documentación para personas) ni a las specs de OpenSpec (comportamiento).
- Documentar detalles que el agente puede deducir leyendo el código.

## Decisions

### Idioma: inglés
Coherente con el código, los commits y los textos de la CLI. Los artefactos de OpenSpec siguen en español, y `AGENTS.md` lo indica explícitamente. *Alternativa:* español, descartada para no mezclar idiomas dentro del código y su tooling.

### CLAUDE.md con `@AGENTS.md`
Claude Code lee `CLAUDE.md` y resuelve importaciones `@ruta`. Un `CLAUDE.md` de una línea mantiene `AGENTS.md` como única fuente de verdad. *Alternativas:* un enlace simbólico, descartado porque es frágil en Windows y en algunos clones; o duplicar el contenido, descartado porque se desincroniza.

### Estructura y longitud de AGENTS.md
Objetivo: menos de unas 120 líneas, en secciones con viñetas y bloques de comandos:

1. **Project overview**: qué es ActivityBookings CLI (cliente de consola de un sistema de reserva de actividades para formación y demos), en dos o tres líneas, y enlace a `docs/api-reference.md` como contrato de la API.
2. **Tech stack**: Python 3.12+, uv, Typer, Rich, httpx, tomllib, pytest, respx, ruff, mypy strict. API con autenticación JWT.
3. **Commands**: `uv sync`, `uv run activity-bookings --help`, `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run mypy src tests`, y la verificación completa antes de terminar una tarea.
4. **Project layout**: el árbol de `src/activity_bookings/` y `tests/` del diseño del esqueleto, con una línea por módulo.
5. **Code conventions**: type hints en todo, funciones pequeñas, dataclasses para los modelos, HTTP solo en la capa de cliente de API, comandos finos que delegan, errores como subclases de `ActivityBookingsError` (mensaje `Error:` y código 1), salida solo mediante las consolas Rich de `console.py`.
6. **Testing**: pytest y `CliRunner`, HTTP siempre mockeado con respx, aislamiento de `HOME`/`XDG_CONFIG_HOME`, un test por escenario de la spec.
7. **OpenSpec workflow**: los cambios de comportamiento pasan por un change (`api-explorer` si toca la API → `/opsx:propose` → `/opsx:apply` → `spec-reviewer` → `/opsx:archive`); las specs viven en `openspec/specs/`; los artefactos van en español y el código en inglés; marcar las tareas solo cuando sus tests pasan.
8. **Boundaries**: no añadir dependencias sin justificarlo en el design; no usar pip ni poetry; no hacer commit ni push sin que se pida; no llamar a la API real en los tests; no editar `uv.lock` a mano.

La sección de layout indica que la estructura es la objetivo del esqueleto. Así un agente no se confunde si la ejecuta antes de que exista el código.

### Subagentes por propósito, no por puesto
Solo se crean subagentes donde un contexto separado aporta algo que la sesión principal no tiene:
- **`spec-reviewer`**: una revisión sin sesgo hecha por quien no escribió el código. Herramientas: Read, Grep, Glob y Bash para `git diff`, `openspec` y los comandos de calidad. No edita nada y devuelve un informe en español con la cobertura de escenarios, los hallazgos y el veredicto.
- **`api-explorer`**: aísla una investigación pesada (leer la copia local `../activity-bookings-express` o clonar el repo de referencia, o consultar una instancia en marcha) y devuelve solo la referencia de endpoints, cuerpos, errores y reglas de negocio. Herramientas: Read, Grep, Glob, Bash y WebFetch. Clona fuera del repositorio y no ejecuta los scripts del repo clonado.

Las instrucciones de los agentes van en inglés, igual que AGENTS.md, y sus informes en español porque los consume el usuario o la fase de planificación. *Alternativa descartada:* agentes por puesto (analista funcional, arquitecto, analista programador). Duplican las fases proposal/specs, design y apply, y cada traspaso entre agentes pierde contexto y gasta tokens.

## Risks / Trade-offs

- [AGENTS.md describe código que aún no existe] → Se marca como estructura objetivo, y la tarea de verificación final de `add-app-skeleton` debería contrastarla. Se recoge como recordatorio en el seguimiento del flujo.
- [`spec-reviewer` da por buenos tests que no comprueban nada] → Se le exige comprobar las cláusulas THEN de cada escenario y citar fichero y línea.
- [La API de referencia cambia o no está disponible] → `api-explorer` indica la fuente y el commit, y lista las dudas en lugar de suponer.
- [El fichero crece y los agentes lo ignoran] → Límite de unas 120 líneas; los detalles se enlazan (`openspec/config.yaml`, specs) en lugar de copiarse.
