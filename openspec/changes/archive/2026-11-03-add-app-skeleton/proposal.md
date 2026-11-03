# Proposal

## Why

El repositorio no tiene todavía código. Antes de implementar cualquier funcionalidad de ActivityBookings (cuenta y login, explorar actividades, reservas, gestión de mis actividades) necesitamos una base de proyecto Python ejecutable, con su tooling de calidad y la configuración de la URL de la API resuelta, para que cada change posterior solo tenga que añadir comandos.

## What Changes

- Proyecto Python gestionado con uv (`pyproject.toml`, layout `src/`, paquete `activity_bookings`, distribución `activity-bookings`).
- Comando de consola `activity-bookings` basado en Typer, con `--help` y `--version`.
- Carga de configuración desde un fichero TOML de usuario con la URL base de la API y valor por defecto cuando el fichero no existe.
- Subcomando `activity-bookings config` que muestra la configuración efectiva (URL de la API y su origen).
- Errores de configuración (TOML inválido, URL no válida) mostrados de forma legible con Rich y código de salida distinto de cero.
- Tooling de calidad configurado y pasando: pytest, ruff (lint + format) y mypy strict.
- `.gitignore` para Python/uv y sección de uso en el README.

### Fuera de alcance

- Cliente HTTP de la API (httpx) y cualquier llamada a ActivityBookings: llega con el primer change funcional.
- Comandos de negocio: cuenta y login, actividades, reservas y gestión de actividades propias.
- Autenticación y almacenamiento del token JWT: llegan con el change de cuenta/sesión.
- Crear o editar el fichero de configuración desde la CLI.
- Distribución/publicación del paquete (PyPI, binarios) y CI.

## Capabilities

### New Capabilities
- `cli-shell`: comando `activity-bookings`, ayuda, versión y política común de errores y códigos de salida.
- `client-config`: ubicación, formato, valores por defecto, validación y visualización de la configuración del cliente.

### Modified Capabilities
<!-- Ninguna: no existen specs previas. -->

## Impact

- Código nuevo: `pyproject.toml`, `uv.lock`, `src/activity_bookings/`, `tests/`, `.gitignore`, `README.md`.
- Dependencias de runtime: `typer`, `rich`. Dependencias de desarrollo: `pytest`, `ruff`, `mypy`.
- Requiere tener uv instalado en la máquina de desarrollo.
