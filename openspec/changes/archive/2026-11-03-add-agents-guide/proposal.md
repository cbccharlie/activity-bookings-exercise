# Proposal

## Why

Los agentes de IA (Claude Code, Copilot, Cursor, Codex…) que trabajan en este repositorio no tienen ahora mismo instrucciones persistentes: no saben qué comandos usar, qué convenciones seguir ni cómo encaja el flujo de OpenSpec. Un `AGENTS.md` en la raíz les da ese contexto en cada sesión y reduce errores repetidos (usar `pip` en vez de `uv`, saltarse mypy, editar código fuera de un change…).

## What Changes

- Nuevo `AGENTS.md` en la raíz, en inglés, con:
  - resumen del proyecto y del stack;
  - comandos de desarrollo con uv (sync, ejecutar la CLI, tests, lint, format, tipos);
  - estructura del paquete prevista en `add-app-skeleton`;
  - convenciones de código, tests y manejo de errores;
  - flujo de trabajo con OpenSpec (propose → apply → archive) y reglas de idioma;
  - límites (qué no debe hacer un agente sin pedir permiso).
- Nuevo `CLAUDE.md` en la raíz que solo importa `@AGENTS.md`, para que Claude Code use la misma fuente de verdad.
- Dos subagentes de Claude Code de solo lectura en `.claude/agents/`:
  - `spec-reviewer`: revisa un change implementado contra sus specs, tareas y las convenciones de AGENTS.md antes de archivarlo;
  - `api-explorer`: investiga la API real de ActivityBookings antes de proponer o diseñar funcionalidades que la consuman.
- AGENTS.md indica cuándo usar cada subagente dentro del flujo de OpenSpec.

### Fuera de alcance

- Cambios en el código, en `pyproject.toml` o en la configuración de OpenSpec.
- Ficheros específicos de otras herramientas (`.github/copilot-instructions.md`, `.cursor/rules`).
- Subagentes por puesto (analista funcional, arquitecto, programador): esos papeles ya los cubren las fases de OpenSpec.
- Hooks, permisos o ajustes de `.claude/settings.json`.

## Capabilities

### New Capabilities
<!-- Ninguna: es documentación para agentes, no cambia el comportamiento del sistema (skip_specs: true). -->

### Modified Capabilities
<!-- Ninguna. -->

## Impact

- Ficheros nuevos: `AGENTS.md`, `CLAUDE.md`, `.claude/agents/spec-reviewer.md`, `.claude/agents/api-explorer.md`.
- Describe el stack y la estructura diseñados en `add-app-skeleton`. Si ese diseño cambia, hay que actualizar `AGENTS.md` en el mismo change.
