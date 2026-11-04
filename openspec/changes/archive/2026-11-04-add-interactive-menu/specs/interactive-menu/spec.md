# Spec Delta

## Purpose

Permite usar la CLI sin recordar subcomandos ni opciones: un menú navegable con flechas y Enter que
pide los datos de cada acción y ejecuta el subcomando correspondiente.

## ADDED Requirements

### Requirement: Menú principal
El sistema SHALL mostrar un menú de selección con flechas y Enter, agrupado por secciones:
actividades (`List activities`, `Show an activity`, `Create an activity`, `Update an activity`,
`Delete an activity`, `Change an activity's status`), reservas (`Book an activity`, `My bookings`,
`Show a booking`), cuenta (`Register`, `Log in`, `Log out`, `Who am I`), `Show configuration` y
`Exit`.

#### Scenario: Opciones del menú
- **WHEN** se abre el menú
- **THEN** la selección ofrece las opciones anteriores en ese orden, terminando en `Exit`

### Requirement: Indicación de la sesión
Cada vez que muestra el menú, el sistema SHALL indicar antes `Logged in as <username>` si hay una
sesión guardada legible, o `Not logged in` en otro caso, sin llamar a la API.

#### Scenario: Cabecera sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** se abre el menú y el usuario elige `Exit`
- **THEN** la salida contiene `Not logged in`
- **AND** no se realiza ninguna petición HTTP
- **AND** el proceso termina con código de salida 0

#### Scenario: Cabecera con sesión
- **GIVEN** una sesión válida del usuario `Ana`
- **WHEN** se abre el menú y el usuario elige `Exit`
- **THEN** la salida contiene `Logged in as Ana`

#### Scenario: Cabecera con un fichero de sesión dañado
- **GIVEN** un fichero de sesión que no es JSON válido
- **WHEN** se abre el menú y el usuario elige `Exit`
- **THEN** la salida contiene `Not logged in`
- **AND** el proceso termina con código de salida 0

### Requirement: Navegación y salida
Tras cada acción el sistema SHALL volver a mostrar el menú. Elegir `Exit` o cancelar la selección
del menú (Esc o Ctrl+C) SHALL cerrarlo con código 0 y sin `Traceback`.

#### Scenario: Salir con Esc o Ctrl+C
- **WHEN** se abre el menú y el usuario cancela la selección (Esc o Ctrl+C)
- **THEN** el menú se cierra sin mostrar `Traceback`
- **AND** el proceso termina con código de salida 0

#### Scenario: Vuelta al menú tras una acción
- **GIVEN** la API responde 200 a `GET /activities` con una lista válida
- **WHEN** el usuario elige `List activities`, deja los filtros vacíos y después elige `Exit`
- **THEN** el menú se muestra dos veces
- **AND** el proceso termina con código de salida 0

### Requirement: Acciones del menú
Cada opción SHALL pedir sus datos y ejecutar el subcomando equivalente con ellos, con el mismo
resultado que si el usuario lo escribiera: mismas peticiones, validación y salida. Un dato opcional
vacío SHALL omitirse. Cancelar un prompt (Esc o Ctrl+C) SHALL volver al menú sin ejecutar nada.
Las confirmaciones y contraseñas que piden los propios subcomandos SHALL pedirse igual que fuera del
menú.

#### Scenario: Abandonar una acción a medias
- **GIVEN** una sesión válida
- **WHEN** el usuario elige `Create an activity` y cancela (Esc o Ctrl+C) al pedir el precio
- **THEN** no se realiza ninguna petición HTTP
- **AND** el menú se vuelve a mostrar

### Requirement: Consulta de actividades
`List activities` SHALL pedir una búsqueda (opcional) y un estado (cualquiera o uno de los seis) y
ejecutar `activities list [--search T] [--status S]`. `Show an activity` SHALL pedir el ID y ejecutar
`activities show ID`.

#### Scenario: Listar actividades con filtros
- **GIVEN** la API responde 200 a `GET /activities` con una lista válida
- **WHEN** el usuario elige `List activities`, escribe `bike` como búsqueda y elige el estado `published`
- **THEN** se realiza la petición `GET /activities` con el parámetro `q=bike`, como `activities list --search bike`
- **AND** la salida contiene la tabla de actividades

#### Scenario: Ver una actividad
- **GIVEN** la API responde 200 a `GET /activities/activity-2` con una actividad válida
- **WHEN** el usuario elige `Show an activity` y escribe `activity-2`
- **THEN** se realiza la petición `GET /activities/activity-2`
- **AND** la salida contiene la ficha de la actividad

### Requirement: Alta y modificación de actividades
`Create an activity` SHALL pedir los campos de `activities create` (duración opcional) y ejecutarlo.
`Update an activity` SHALL pedir el ID y cada campo, todos opcionales, y ejecutar
`activities update` solo con los indicados.

#### Scenario: Crear una actividad sin duración
- **GIVEN** una sesión válida
- **AND** la API responde 201 a `POST /activities` con la actividad `activity-5`
- **WHEN** el usuario elige `Create an activity` e introduce `Yoga`, `20`, `2027-01-15`, `Park`, `2`, `10` y deja la duración vacía
- **THEN** el cuerpo JSON enviado es `{"name": "Yoga", "price": 20, "date": "2027-01-15", "location": "Park", "minParticipants": 2, "maxParticipants": 10}`
- **AND** la salida contiene `Activity activity-5 created.`

#### Scenario: Modificar solo el precio
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `PUT /activities/activity-5` con una actividad válida
- **WHEN** el usuario elige `Update an activity`, escribe `activity-5`, introduce `25` como precio y deja vacíos los demás campos
- **THEN** el cuerpo JSON enviado es `{"price": 25}`

### Requirement: Borrado y cambio de estado desde el menú
`Delete an activity` SHALL pedir el ID y confirmación, y ejecutar `activities delete ID --yes` solo
si se confirma. `Change an activity's status` SHALL pedir el ID y el estado (lista de los seis),
pedir confirmación solo para `done` o `cancelled`, y ejecutar `activities status ID ESTADO --yes`
salvo que no se confirme.

#### Scenario: Borrado confirmado desde el menú
- **GIVEN** una sesión válida
- **AND** la API responde 204 a `DELETE /activities/activity-5`
- **WHEN** el usuario elige `Delete an activity`, escribe `activity-5` y confirma
- **THEN** se realiza exactamente una petición `DELETE /activities/activity-5`
- **AND** la salida contiene `Activity activity-5 deleted.`

#### Scenario: Borrado rechazado desde el menú
- **GIVEN** una sesión válida
- **WHEN** el usuario elige `Delete an activity`, escribe `activity-5` y no confirma
- **THEN** no se realiza ninguna petición HTTP
- **AND** el menú se vuelve a mostrar

#### Scenario: Publicar desde el menú sin confirmación
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `PATCH /activities/activity-5/status` con la actividad en estado `published`
- **WHEN** el usuario elige `Change an activity's status`, escribe `activity-5` y elige `published`
- **THEN** no se pide confirmación
- **AND** el cuerpo JSON enviado es `{"status": "published"}`
- **AND** la salida contiene `Activity activity-5 is now published.`

#### Scenario: Cancelación rechazada desde el menú
- **GIVEN** una sesión válida
- **WHEN** el usuario elige `Change an activity's status`, escribe `activity-5`, elige `cancelled` y no confirma
- **THEN** no se realiza ninguna petición HTTP

### Requirement: Acciones sobre reservas, cuenta y configuración
Las demás opciones SHALL equivaler a:

| Opción | Datos | Subcomando |
|---|---|---|
| Book an activity | ID, plazas (1 por defecto) | `bookings create ID --participants N` |
| My bookings | ID de actividad (opcional) | `bookings list [--activity ID]` |
| Show a booking | ID | `bookings show ID` |
| Register / Log in | usuario y email / email | `auth register ...` / `auth login --email E` |
| Log out / Who am I | — | `auth logout` / `auth whoami` |
| Show configuration | — | `config` |

#### Scenario: Ver una reserva desde el menú
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings/booking-1` con una reserva válida
- **WHEN** el usuario elige `Show a booking` y escribe `booking-1`
- **THEN** se realiza la petición `GET /bookings/booking-1`
- **AND** la salida contiene la ficha de la reserva

#### Scenario: Mis reservas sin filtro
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /bookings` con `[]`
- **WHEN** el usuario elige `My bookings` y deja el filtro vacío
- **THEN** la petición no lleva el parámetro `activityId`
- **AND** la salida contiene `No bookings found.`

#### Scenario: Reservar plazas desde el menú
- **GIVEN** una sesión válida
- **AND** la API responde 200 a `GET /activities/activity-2` con una actividad publicada y futura
- **AND** la API responde 201 a `POST /bookings` con una reserva válida
- **WHEN** el usuario elige `Book an activity`, escribe `activity-2`, introduce `2` plazas y confirma la reserva cuando el subcomando lo pide
- **THEN** el cuerpo JSON enviado a `POST /bookings` es `{"activityId": "activity-2", "participants": 2}`

#### Scenario: Cerrar sesión desde el menú
- **GIVEN** una sesión válida
- **WHEN** el usuario elige `Log out` y después `Exit`
- **THEN** el fichero de sesión ya no existe
- **AND** no se realiza ninguna petición HTTP

#### Scenario: Ver la configuración desde el menú
- **WHEN** el usuario elige `Show configuration`
- **THEN** la salida contiene `API URL`

### Requirement: Errores dentro del menú
Cuando el subcomando de una acción falla, el sistema SHALL mostrar su error igual que fuera del
menú y volver al menú, sin terminar el proceso ni mostrar `Traceback`.

#### Scenario: Error de la API y vuelta al menú
- **GIVEN** una sesión válida
- **AND** la API responde 404 a `GET /activities/activity-99` con `{"message": "Activity not found", "errors": []}`
- **WHEN** el usuario elige `Show an activity`, escribe `activity-99` y después elige `Exit`
- **THEN** la salida de error contiene `Error: Activity not found`
- **AND** el menú se vuelve a mostrar
- **AND** el proceso termina con código de salida 0

#### Scenario: Dato no válido y vuelta al menú
- **GIVEN** una sesión válida
- **WHEN** el usuario elige `Create an activity`, introduce `abc` como precio y el resto de datos válidos, y después elige `Exit`
- **THEN** la salida de error menciona `--price`
- **AND** no se realiza ninguna petición HTTP
- **AND** el menú se vuelve a mostrar

#### Scenario: Acción protegida sin sesión
- **GIVEN** no existe el fichero de sesión
- **WHEN** el usuario elige `My bookings`, deja el filtro vacío y después elige `Exit`
- **THEN** la salida de error contiene `Error: not logged in` y `activity-bookings auth login`
- **AND** no se realiza ninguna petición HTTP
- **AND** el menú se vuelve a mostrar

#### Scenario: API caída dentro del menú
- **GIVEN** la conexión con la API es rechazada
- **WHEN** el usuario elige `List activities`, deja los filtros vacíos y después elige `Exit`
- **THEN** la salida de error contiene `Error: cannot connect to the API at http://localhost:3000`
- **AND** el proceso termina con código de salida 0

### Requirement: Configuración en el menú
Si el usuario arranca el menú con `--config <ruta>`, todas las acciones SHALL usar esa
configuración.

#### Scenario: Menú con otro fichero de configuración
- **GIVEN** un fichero `custom.toml` con `api_url = "http://api.example.com"`
- **AND** la API responde 200 a `GET http://api.example.com/activities` con una lista válida
- **WHEN** el usuario ejecuta `activity-bookings --config custom.toml` en un terminal, elige `List activities` con los filtros vacíos y después `Exit`
- **THEN** se realiza la petición `GET http://api.example.com/activities`
