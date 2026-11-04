---
name: smoke-test
description: Prueba la CLI activity-bookings de punta a punta contra la API real en marcha (registro, actividades, reservas, borrado) y compara lo que pasa con docs/api-reference.md. Úsala cuando el usuario quiera probar, lanzar o ver funcionando la CLI de verdad, comprobar un change contra el servidor antes de archivarlo, o detectar si la API se comporta distinto de lo documentado ("pruébalo contra la API", "haz un smoke test", "¿funciona de verdad?"), aunque no diga "smoke test".
---

# Smoke test contra la API real

Los tests de pytest mockean todo el HTTP con respx. Esta skill es lo único que ejecuta la CLI
contra el servidor de verdad. No es un test automático ni forma parte del check: es una
verificación manual, útil antes de `/opsx:archive`.

Argumento opcional: el nombre de un change o de un grupo de comandos (`bookings`, `activities`,
`auth`). Si llega, ejecuta solo los pasos que tocan esos comandos, más los imprescindibles para
llegar a ellos (registro, crear y publicar la actividad).

## 1. Preparar un entorno aislado

No toques la sesión ni la configuración real del usuario.

```bash
SMOKE=<scratchpad>/smoke-$(date +%s)          # directorio temporal del scratchpad
mkdir -p "$SMOKE/activity-bookings"
cp ~/.config/activity-bookings/config.toml "$SMOKE/activity-bookings/" 2>/dev/null || true
export XDG_CONFIG_HOME="$SMOKE"
```

Copiar el `config.toml` conserva la `api_url` que use el usuario. Exporta `XDG_CONFIG_HOME` en
cada llamada a Bash (el entorno no persiste entre llamadas).

## 2. Comprobar que la API responde

Saca la URL con `uv run activity-bookings config` y llama a `GET <api_url>/health`
(`curl -sf`). Si no responde, **para**: di la URL probada y que hay que levantar el servidor
(`npm run dev` en el repositorio de la API, puerto 3000 por defecto). No lo arranques tú salvo que
el usuario lo pida.

## 3. Recorrer el flujo

Ejecuta cada paso con `uv run activity-bookings ...` y apunta el código de salida y lo relevante
de la salida. Si un paso falla, sigue con los que no dependan de él.

| # | Comando | Espera |
|---|---|---|
| 1 | `printf 'Smoke1234\nSmoke1234\n' \| uv run activity-bookings auth register --username smoke-<ts> --email smoke-<ts>@example.com --accept-terms` | 0, sesión creada |
| 2 | `auth whoami` | 0, muestra el usuario |
| 2b | `curl -s <api_url>/activities` | guarda los IDs que ya existen |
| 3 | `activities create --name "Smoke <ts>" --price 10 --date <hoy+30d> --location Test --min-participants 1 --max-participants 3` | 0, anota el ID |
| 4 | `activities status <id> published --yes` | 0 |
| 5 | `activities list --search "Smoke <ts>"` y `activities show <id>` | 0, aparece publicada |
| 6 | `bookings create <id> --participants 2 --yes` | 0, anota el ID de reserva |
| 7 | `bookings create <id> --participants 2 --yes` | ≠0, capacidad superada |
| 8 | `bookings list --activity <id>` y `bookings show <booking-id>` | 0 |
| 9 | `activities delete <id> --yes` (solo si el ID es nuevo, ver abajo) | 0 |
| 10 | `activities show <id>` (solo si se hizo el 9) | ≠0, no existe |
| 11 | `auth logout` y luego `bookings list` | 0, y ≠0 con pista de login |

Usa `<ts>` = timestamp para no chocar con ejecuciones anteriores (los datos persisten en `db/`).
Si el change que se prueba añade comandos nuevos, añade sus pasos en el punto lógico del flujo.

Fallos conocidos del servidor (`docs/api-reference.md`, Discrepancias, punto 1):

- `auth login` falla con 401 incluso con el usuario recién registrado. Por eso el flujo usa el
  token del registro y no prueba el login; si se prueba, ese 401 es lo esperado.
- Los contadores de ID empiezan en 1 y **sobrescriben actividades existentes** (confirmado el
  2026-11-04: la prueba recibió `activity-4` y sustituyó a la de la semilla). Avisa al usuario
  antes de empezar de que la prueba escribe en el servidor.
- **Nunca borres un ID que ya existía.** Si el ID del paso 3 está en la lista del paso 2b, sáltate
  los pasos 9 y 10 y deja la actividad como está. Borrarla haría desaparecer ese ID del servidor
  (los datos de la semilla ya se habrán perdido al sobrescribirse, pero el ID al menos sigue
  existiendo para quien lo use en pruebas). Dilo en el informe: qué ID se sobrescribió y que se
  ha dejado sin borrar.

## 4. Informar

Tabla breve: paso, comando, código de salida, OK/fallo. Debajo, solo lo que importa:

- Fallos de la CLI (traceback, mensaje confuso, código de salida incorrecto): son bugs nuestros.
- Comportamientos de la API distintos de `docs/api-reference.md`: cítalos con la sección y
  propón volver a pasar el subagente `api-explorer` para actualizar la referencia.

## 5. Limpiar

Borra `$SMOKE`. En la API quedan el usuario de prueba y la reserva (la API no permite borrar
usuarios ni reservas), y también la actividad si se saltó su borrado; dilo en una línea.
Nunca borres ni edites a mano los ficheros `db/` del servidor.
