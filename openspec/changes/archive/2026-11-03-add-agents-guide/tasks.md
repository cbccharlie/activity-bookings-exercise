# Tasks

## 1. AGENTS.md

- [x] 1.1 Crear `AGENTS.md` en inglés con las secciones «Project overview», «Tech stack» y «Commands» según `design.md`, y verificar que cada comando listado coincide con los de `add-app-skeleton/design.md` y `openspec/config.yaml`
- [x] 1.2 Añadir las secciones «Project layout» (marcada como estructura objetivo mientras el esqueleto no esté aplicado), «Code conventions» y «Testing», y verificar que los nombres de módulos y la política de errores coinciden con `add-app-skeleton/design.md`
- [x] 1.3 Añadir las secciones «OpenSpec workflow» y «Boundaries», y verificar que los comandos `/opsx:*` citados existen en `.claude/commands/opsx/`
- [x] 1.4 Revisar la longitud y la claridad, y verificar que `wc -l AGENTS.md` da 120 líneas o menos y que no hay contenido duplicado de `openspec/config.yaml` más allá de lo necesario

## 2. CLAUDE.md

- [x] 2.1 Crear `CLAUDE.md` con una breve línea de cabecera y `@AGENTS.md`, y verificar que al iniciar Claude Code en el repo las instrucciones de AGENTS.md aparecen en la memoria cargada (`/memory`)

## 3. Subagentes

- [x] 3.1 Crear `.claude/agents/spec-reviewer.md` (solo lectura: Read, Grep, Glob, Bash) con el procedimiento de revisión y el formato de informe, y verificar que su frontmatter tiene `name`, `description` y `tools`
- [x] 3.2 Crear `.claude/agents/api-explorer.md` (Read, Grep, Glob, Bash, WebFetch) apuntando al repo de referencia `activity-bookings-express`, y verificar que su frontmatter tiene `name`, `description` y `tools`
- [x] 3.3 Mencionar ambos subagentes en la sección «OpenSpec workflow» de AGENTS.md y verificar en `/agents` (Claude Code) que aparecen como agentes del proyecto

## 4. Verificación final

- [x] 4.1 Verificar que `openspec validate add-agents-guide` pasa y, si `add-app-skeleton` ya está aplicado, ejecutar `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests` y `uv run pytest` comprobando que los comandos documentados en AGENTS.md funcionan tal como están escritos

## Workflow follow-up

- Al aplicar o archivar `add-app-skeleton`, contrastar la sección «Project layout» de AGENTS.md con la estructura real y quitar la marca de estructura objetivo.
