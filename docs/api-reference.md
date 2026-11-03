# Referencia de la API ActivityBookings

> Generado el 2026-11-03 con el subagente `api-explorer`, leyendo el código (sin ejecutar el servidor) del repositorio de referencia `activity-bookings-express@68704a5`. Las citas `fichero:línea` son relativas a la raíz de ese repositorio.
> Si la API cambia, hay que volver a ejecutar `api-explorer` y regenerar este documento.

> **Conceptos clave para el cliente.** La API gestiona **activities** (actividades) y **bookings** (reservas) de un sistema de reservas para formación y demos.
>
> | Concepto del cliente CLI | Concepto en la API | Origen |
> |---|---|---|
> | Actividad | `Activity` | `src/types/activity.ts:15-29` |
> | Precio | `Activity.price` (por plaza) | `src/types/activity.ts:19` |
> | Capacidad total | `Activity.maxParticipants` | `src/types/activity.ts:24` |
> | Plazas libres | **No se expone.** Hay que calcularlas (ver Reglas) | `src/services/booking.service.ts:127-138`, `PRD.md:72-74` (FR7 "NotStarted") |
> | Plazas reservadas | `Booking.participants` | `src/types/booking.ts:10` |
> | Estado de la reserva | **No hay estado de reserva.** Solo existe `paymentStatus` en la reserva y `activity.status` de la actividad | `src/types/booking.ts:13`, `src/types/booking.ts:36` |
> | Usuario | `User`, identificado por el JWT | `src/middleware/auth.middleware.ts:26-30` |

---

## Aspectos generales

### URL base y puerto
- `http://localhost:3000` por defecto. Se cambia con la variable de entorno `PORT` (`src/index.ts:14`, `README.md:37`).
- No hay prefijo de versión ni `/api`. Las rutas se montan en la raíz (`src/index.ts:27-30`).
- CORS está abierto a todos los orígenes con `cors()` (`src/index.ts:16`).
- El cuerpo de las peticiones es JSON con `express.json()` (`src/index.ts:17`). El cliente debe enviar `Content-Type: application/json`.
- Scripts (`package.json:6-11`): `dev` (tsx), `build` (tsc), `start` (que ejecuta `prestart` → build) y `typecheck`. No hay script `test`, aunque `AGENTS.md:34` mencione `npm test`.

### Autenticación
- JWT en la cabecera `Authorization: Bearer <token>` (`src/middleware/auth.middleware.ts:12-13`).
  - El middleware toma lo que va **después del primer espacio** (`split(' ')[1]`) y no comprueba que la palabra sea literalmente `Bearer`.
- Contenido del token: `{ userId: "user-N", email }` (`src/types/auth.ts:6-9`, `src/utils/jwt.ts:9-11`).
- Caduca a las **24 h** (`src/utils/jwt.ts:11`).
- Secreto: `JWT_SECRET`, o `development-secret-key-change-in-production` si no está definido (`src/utils/jwt.ts:4`).
- El token se obtiene con `POST /login` o con `POST /users`. Los dos devuelven `accessToken`.
- No hay refresh token ni logout.
- **Cómo se identifica al cliente:** con el `userId` del JWT. El servidor lo añade a `req.user` (`src/middleware/auth.middleware.ts:27-30`). Ningún endpoint acepta un `userId` en el cuerpo o en la query; las reservas se asignan y filtran siempre por el token (`src/routes/bookings.ts:37`, `src/routes/bookings.ts:118`).

Endpoints públicos y protegidos:

| Endpoint | Necesita token |
|---|---|
| `GET /`, `GET /health` | No |
| `POST /users`, `POST /login` | No |
| `GET /activities`, `GET /activities/:id` | No |
| `POST /activities`, `PUT /activities/:id`, `DELETE /activities/:id`, `PATCH /activities/:id/status` | Sí |
| Todo `/bookings` | Sí |

### Formato de las respuestas
- **Las respuestas correctas no van envueltas.** Se devuelve directamente la entidad o un array JSON (`src/routes/activities.ts:129`, `src/routes/activities.ts:156`, `src/routes/bookings.ts:46`).
- **Todos los errores** tienen este formato (`src/types/error.ts:4-16`, `ADD.md:175-199`):
  ```json
  { "message": "Validation failed", "errors": [ { "field": "participants", "message": "..." } ] }
  ```
  - `errors` lleva un elemento por campo cuando es un error de validación (400).
  - En cualquier otro error, `errors` es `[]`.
- Las validaciones devuelven **todos** los errores a la vez, no solo el primero (`src/services/activity.service.ts:230-348`).

### Paginación y filtros
- **No hay paginación.** `GET /activities` y `GET /bookings` devuelven la colección completa (`src/routes/activities.ts:112-129`, `src/routes/bookings.ts:25-46`).
- Filtros de `GET /activities`: `q`, `slug`, `_sort`, `_order`.
- Filtro de `GET /bookings`: `activityId`.

### Formato de los IDs
- Cadenas con el patrón `<recurso>-<n>`: `activity-1`, `booking-1`, `payment-1`, `user-1`.
  - Activities: `src/services/activity.service.ts:61`
  - Bookings: `src/services/booking.service.ts:83`
  - Payments: `src/services/payment.service.ts:68`
  - Users: `src/services/user.service.ts:73`
- **Excepción:** `POST /login` y `POST /users` devuelven `user.id` como **número** (`1`), que se obtiene con `parseInt(id.replace('user-',''))` (`src/routes/auth.ts:32`, `src/routes/users.ts:32`, `src/types/auth.ts:16`). En cambio, en las reservas `userId` es la cadena `"user-1"` (`src/types/booking.ts:9`).
- Los tipos de `client/` (por ejemplo `client/activity.type.ts:18`, `client/booking.type.ts:18-21`) declaran los IDs como `number` y **no coinciden con lo que devuelve el servidor**. No hay que usarlos como contrato.

### Formato de las fechas
- `Activity.date` es una cadena ISO 8601 y puede ser **solo fecha** (`"2026-10-26"`, `db/activities.json:7`) o fecha y hora en UTC (`"2026-08-25T14:00:00.000Z"`, `db/activities.json:35`).
- `createdAt` y `updatedAt` se generan con `new Date().toISOString()`, por ejemplo `"2026-01-26T09:52:15.182Z"` (`src/services/activity.service.ts:63`, `src/services/booking.service.ts:92`).

### Persistencia y datos de ejemplo
- Los datos se guardan en ficheros JSON dentro de `db/` (`src/utils/data-loader.ts:11-14`).
- Al arrancar, `db/seed/activities.json` se fusiona con `db/activities.json`. Si un ID está en los dos, **gana el persistido** (`src/repositories/json.repository.ts:29-72`).
- **Datos efectivos al arrancar** (los persistidos sustituyen a los cuatro IDs de la semilla):

| id | name | price | date | maxParticipants | minParticipants | status | Fuente |
|---|---|---|---|---|---|---|---|
| `activity-1` | Surf | 158 | `2026-10-26` (ya pasada) | 8 | 2 | `draft` | `db/activities.json:2-15` |
| `activity-2` | City Bike Tour | 35 | `2026-12-20` | 15 | 3 | `published` | `db/activities.json:16-29` |
| `activity-3` | Cooking Workshop: Italian Cuisine | 75 | `2026-08-25T14:00:00.000Z` (ya pasada) | 12 | 4 | `published` | `db/activities.json:30-43` |
| `activity-4` | Photography Walk | 30 | `2027-03-01T09:00:00.000Z` | 10 | 2 | `draft` | `db/activities.json:44-57` |

  - Todas pertenecen a `userId: "user-1"`.
  - `activity-2` es la única que está `published` y tiene fecha futura. Es la mejor candidata para las pruebas de reserva.
- **Usuarios:** solo hay uno, `user-1` (`username: "Mark Musk"`, `email: "m@f.c"`, `password: "1234aB"`, `terms: true`) (`db/users.json:2-9`). La contraseña está en texto plano y se compara tal cual (`src/services/user.service.ts:125`).
- **Reservas y pagos:** los dos ficheros están vacíos (`[]`) (`db/bookings.json:1`, `db/payments.json:1`).

---

## Sistema

### GET /
- **Propósito:** comprobar que el servidor responde.
- **Respuesta 200:**
  ```json
  {"status":"ok","message":"ActivityBookings API"}
  ```
  (`src/index.ts:19-21`)

### GET /health
- **Propósito:** health check.
- **Respuesta 200:**
  ```json
  {"status":"ok"}
  ```
  (`src/index.ts:23-25`)

---

## Usuarios y autenticación

### POST /users
- **Propósito:** registrar un usuario. Devuelve el token directamente.
- **Petición** (`src/services/user.service.ts:137-172`):

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `username` | string | sí | no puede estar vacío |
| `email` | string | sí | debe cumplir `^[^\s@]+@[^\s@]+\.[^\s@]+$`; se guarda en minúsculas (`:77`) |
| `password` | string | sí | 6 caracteres como mínimo |
| `terms` | boolean | sí | tiene que ser exactamente `true` |

- **Respuesta 201** (`src/routes/users.ts:30-39`):
  ```json
  {"user":{"id":2,"username":"Ana","email":"ana@example.com","terms":true},"accessToken":"eyJhbGciOi..."}
  ```
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 400 | Validación | `{"message":"Validation failed","errors":[{"field":"terms","message":"Terms acceptance is required"}, ...]}` (`src/routes/users.ts:19-25`) |
| 400 | Email ya registrado | `{"message":"Email is already registered","errors":[{"field":"email","message":"Email is already registered"}]}` (`src/routes/users.ts:42-50`) |
| 400 | Cualquier otro fallo | `{"message":"Failed to register user","errors":[]}` |

### POST /login
- **Propósito:** iniciar sesión y obtener el JWT.
- **Petición** (`src/services/user.service.ts:178-198`):

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `email` | string | sí | no puede estar vacío; se busca sin distinguir mayúsculas (`:102`) |
| `password` | string | sí | no puede estar vacío |

- **Respuesta 200** (`src/routes/auth.ts:30-39`):
  ```json
  {"user":{"id":1,"username":"Mark Musk","email":"m@f.c","terms":true},"accessToken":"eyJhbGciOi..."}
  ```
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 400 | Validación | `{"message":"Validation failed","errors":[{"field":"email","message":"Email is required and must be a non-empty string"}]}` (`src/routes/auth.ts:19-25`) |
| 401 | Credenciales incorrectas | `{"message":"Invalid email or password","errors":[]}` (`src/routes/auth.ts:41-48`) |
| 401 | Otro fallo | `{"message":"Authentication failed","errors":[]}` |

> Hay un posible fallo que puede romper el login con los usuarios de la semilla. Ver Discrepancias, punto 1.

### Errores comunes a todas las rutas protegidas (middleware)

| Código | Condición | Cuerpo |
|---|---|---|
| 401 | Falta la cabecera o el token | `{"message":"Authentication required. Please provide a valid token.","errors":[]}` (`src/middleware/auth.middleware.ts:15-23`) |
| 401 | Token inválido o caducado | `{"message":"Invalid or expired token. Please login again.","errors":[]}` (`src/middleware/auth.middleware.ts:32-39`) |

---

## Actividades

### GET /activities ★
- **Propósito:** listar las actividades. Es público.
- **Parámetros de query** (`src/routes/activities.ts:112-127`, `src/services/activity.service.ts:98-162`):

| Parámetro | Tipo | Efecto |
|---|---|---|
| `q` | string | busca la subcadena, sin distinguir mayúsculas, en `name`, `location` y `slug` |
| `slug` | string | coincidencia exacta con `slug` |
| `_sort` | string | campo por el que ordenar; `date`, `createdAt` y `updatedAt` se ordenan como fechas, los números como números y el resto como cadenas |
| `_order` | `asc` \| `desc` | por defecto `asc`; **se ignora si no se envía `q`, `slug` o `_sort`** (`:115`) |

- **No hay filtro por `status`.** El cliente tiene que filtrar por su cuenta, por ejemplo para quedarse solo con las `published`.
- **Respuesta 200:** array de `Activity` (`src/types/activity.ts:15-29`).
  ```json
  [{"id":"activity-2","name":"City Bike Tour","slug":"city-bike-tour","price":35,"date":"2026-12-20","duration":120,"location":"City Center","minParticipants":3,"maxParticipants":15,"status":"published","userId":"user-1","createdAt":"2026-01-16T10:00:00.000Z"}]
  ```
  `updatedAt` es opcional y solo aparece si la actividad se ha modificado.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 500 | Excepción interna | `{"message":"Failed to retrieve activities","errors":[]}` (`src/routes/activities.ts:130-137`) |

### GET /activities/:id ★
- **Propósito:** ver el detalle de una actividad. Es público.
- **Respuesta 200:** un objeto `Activity`, con la misma forma que en el listado (`src/routes/activities.ts:146-156`).
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 404 | El ID no existe | `{"message":"Activity not found","errors":[]}` (`:149-154`) |
| 500 | Excepción interna | `{"message":"Failed to retrieve activity","errors":[]}` |

- **No informa de las plazas ocupadas ni de las libres** (ver Reglas).

### POST /activities
- **Propósito:** crear una actividad. Necesita token y la actividad queda a nombre del usuario del token (`src/routes/activities.ts:65-99`).
- **Petición:** los campos `price`, `duration`, `minParticipants` y `maxParticipants` aceptan números o cadenas numéricas (`:18-57`).

| Campo | Tipo | Obligatorio | Regla (`src/services/activity.service.ts:230-348`) |
|---|---|---|---|
| `name` | string | sí | no puede estar vacío |
| `price` | number | sí | mayor que 0 |
| `date` | string ISO | sí | debe ser válida y **futura** |
| `duration` | number | no (por defecto 60) | mayor que 0, en minutos |
| `location` | string | sí | no puede estar vacío |
| `minParticipants` | number | sí | 1 o más, y menor o igual que `maxParticipants` |
| `maxParticipants` | number | sí | 1 o más |
| `status` | ActivityStatus | no (por defecto `draft`) | uno de los seis estados; aquí **no** se comprueba la máquina de estados |

  El `slug` se genera a partir de `name` (`src/services/activity.service.ts:510-518`).
- **Respuesta 201:** la `Activity` creada.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 400 | Validación | `{"message":"Validation failed","errors":[...]}` |
| 400 | Otro fallo | `{"message":"Failed to create activity","errors":[]}` |
| 401 | Sin token o token inválido | ver middleware |

### PUT /activities/:id
- **Propósito:** modificar una actividad. Necesita token y solo puede hacerlo su dueño (`src/routes/activities.ts:173-226`).
- **Petición:** los mismos campos que en el alta, todos opcionales. Aquí los números tienen que ser de tipo `number`, no se aceptan cadenas (`src/services/activity.service.ts:354-441`).
  - Si se envía `status`, da error 400 con el mensaje `"Status cannot be changed via PUT endpoint. Use PATCH /activities/:id/status to transition status."` (`:433-438`).
  - Si cambia `name`, se vuelve a generar el `slug`.
- **Respuesta 200:** la `Activity` actualizada, con `updatedAt`.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 404 | El ID no existe (se comprueba **antes** que el token del usuario) | `"Activity not found"` |
| 400 | Validación | `"Validation failed"` |
| 403 | No es el dueño | `"You can only update your own activities"` |
| 401 | Sin token | ver middleware |

### DELETE /activities/:id
- **Propósito:** borrar una actividad. Necesita token y solo puede hacerlo su dueño (`src/routes/activities.ts:234-271`).
- **Respuesta 204:** sin cuerpo.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 404 | El ID no existe | `"Activity not found"` |
| 403 | No es el dueño | `"You can only delete your own activities"` |
| 500 | Otro fallo | `"Failed to delete activity"` |

- No se comprueba si la actividad tiene reservas. Ver Discrepancias, punto 7.

### PATCH /activities/:id/status
- **Propósito:** cambiar el estado de una actividad. Necesita token y solo puede hacerlo su dueño (`src/routes/activities.ts:279-347`).
- **Petición:** `{ "status": "<ActivityStatus>" }`.
- **Respuesta 200:** la `Activity` con el nuevo `status` y `updatedAt` (`src/services/activity.service.ts:474-504`).
- **Errores:**

| Código | Condición | Mensaje |
|---|---|---|
| 400 | El cuerpo no es un objeto | `"Request body must be a valid JSON object"` |
| 400 | Falta `status` o no es una cadena | `"Status field is required and must be a string"` |
| 400 | Estado desconocido | `"Invalid status. Status must be one of: draft, published, confirmed, sold-out, done, cancelled"` |
| 400 | Transición no permitida | `"Invalid status transition from draft to done. Valid transitions are: published"` |
| 403 | No es el dueño | `"You can only transition your own activities"` |
| 404 | El ID no existe | `"Activity not found"` |

  En todos los casos `errors` es `[]`.

#### Máquina de estados de la actividad
Origen: `src/services/activity.service.ts:447-458`.

| Desde | Hacia |
|---|---|
| `draft` | `published` |
| `published` | `confirmed`, `cancelled`, `sold-out` |
| `confirmed` | `done`, `cancelled` |
| `sold-out` | `confirmed` |
| `done` | — (estado final) |
| `cancelled` | — (estado final) |

- Ninguna transición es automática. `sold-out` **no** se activa solo al agotarse las plazas, aunque la spec diga que "puede" (`specs/feat-activity-status-lifecycle.spec.md:32`). No hay ningún código que lo haga.

---

## Reservas

### POST /bookings ★
- **Propósito:** reservar plazas en una actividad. Necesita token. La reserva queda a nombre del usuario del token y el pago se cobra en el mismo momento (`src/routes/bookings.ts:98-144`, `src/services/booking.service.ts:66-113`).
- **Petición** (`src/services/booking.service.ts:213-236`):

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `activityId` | string | sí | no puede estar vacío, por ejemplo `"activity-2"` |
| `participants` | number | sí | **de tipo `number`** (la cadena `"2"` se rechaza) y 1 o más; no se exige que sea entero |

- **Orden en que se procesa:**
  1. Validación (400).
  2. ¿Existe la actividad? (404).
  3. Capacidad: si `participants` supera las plazas disponibles, error 400.
  4. Importe: `amount = price × participants`.
  5. Cobro en la pasarela simulada (402 si falla).
  6. Se guarda el pago (`paid`) y después la reserva (201).
- **Respuesta 201:** devuelve la `Booking` tal como se guarda, **sin** el objeto `activity` (`src/routes/bookings.ts:118-119`, `src/services/booking.service.ts:95-103`). La forma está sacada del código y los valores son de ejemplo:
  ```json
  {"id":"booking-1","activityId":"activity-2","userId":"user-1","participants":2,"createdAt":"2026-11-03T10:00:00.000Z","paymentId":"payment-1","paymentStatus":"paid"}
  ```
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 400 | Validación | `{"message":"Validation failed","errors":[{"field":"participants","message":"Participants is required and must be a positive number (at least 1)"}]}` (`:100-107`) |
| 400 | Se piden más plazas de las que quedan | `{"message":"Capacity exceeded. Available: 13, Requested: 20","errors":[]}` (`src/services/booking.service.ts:79`, `src/routes/bookings.ts:129-131`) |
| 401 | Sin token o token inválido | ver middleware |
| 402 | La pasarela rechaza el cobro: ocurre cuando el importe es mayor que 0 y múltiplo de 1000 (`src/services/mock-payment-gateway.ts:10-18`) | `{"message":"Payment could not be processed","errors":[]}` (`src/routes/bookings.ts:132-135`) |
| 404 | `activityId` no existe | `{"message":"Activity not found","errors":[]}` (`:126-128`) |
| 400 | Otro fallo | `{"message":"Failed to create booking","errors":[]}` |

  Cuando falla el pago no se crea ni la reserva ni el pago.

### GET /bookings ★
- **Propósito:** ver las reservas del usuario del token (`src/routes/bookings.ts:25-55`).
- **Query:** `activityId` (opcional) devuelve solo las reservas de esa actividad (`:40-43`).
- **Respuesta 200:** array de `BookingResponse`, es decir, cada reserva con los datos de su actividad y el estado del pago (`src/types/booking.ts:42-51`, `src/services/booking.service.ts:175-199`):
  ```json
  [{"id":"booking-1","activityId":"activity-2","userId":"user-1","participants":2,"createdAt":"2026-11-03T10:00:00.000Z","paymentId":"payment-1","paymentStatus":"paid",
    "activity":{"name":"City Bike Tour","slug":"city-bike-tour","price":35,"date":"2026-12-20","duration":120,"location":"City Center","status":"published"}}]
  ```
  - `paymentStatus` es `pending` si la reserva no lo tiene guardado (`src/services/booking.service.ts:205-207`).
  - Si el usuario no tiene reservas, devuelve `[]`.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 401 | Sin token o token inválido | ver middleware |
| 500 | Excepción interna, por ejemplo una actividad borrada (ver Discrepancias, punto 7) | `{"message":"Failed to retrieve bookings","errors":[]}` |

### GET /bookings/:id ★
- **Propósito:** ver el detalle de una reserva propia (`src/routes/bookings.ts:63-90`).
- **Respuesta 200:** un `BookingResponse`, con la misma forma que en el listado.
- **Errores:**

| Código | Condición | Cuerpo |
|---|---|---|
| 404 | La reserva no existe **o es de otro usuario** (no se revela que exista) | `{"message":"Booking not found","errors":[]}` (`src/services/booking.service.ts:160-169`) |
| 500 | Otro fallo | `{"message":"Failed to retrieve booking","errors":[]}` |
| 401 | Sin token | ver middleware |

- **No hay endpoints para cancelar, modificar ni borrar reservas.** Las únicas rutas de reservas son `GET /`, `GET /:id` y `POST /` (`src/routes/bookings.ts:25`, `:63`, `:98`).

---

## Reglas de negocio

1. **Plazas disponibles:** se calculan como `maxParticipants` menos la suma de `participants` de **todas** las reservas de esa actividad, de cualquier usuario, y nunca bajan de 0 (`src/services/booking.service.ts:127-138`).
   - La API no ofrece este dato. Si el CLI quiere mostrar las plazas libres, solo ve las reservas del propio usuario (`GET /bookings` filtra por el token), así que **no puede calcularlas de forma exacta**.
   - Lo que sí puede hacer: mostrar `maxParticipants` como capacidad total y usar el error 400 `Capacity exceeded. Available: N, Requested: M` para saber cuántas plazas quedan de verdad. Esto es una inferencia.
2. **Para no superar las plazas,** el servidor rechaza `participants > disponibles`. Reservar exactamente las que quedan sí está permitido (`src/services/booking.service.ts:78`).
3. **No se comprueba el estado ni la fecha de la actividad al reservar** (`src/services/booking.service.ts:66-113`). Se puede reservar una actividad `draft`, `cancelled`, `done`, `sold-out` o ya pasada. Si el cliente quiere ofrecer solo actividades reservables, debe filtrar él (por ejemplo `status == "published"` y fecha futura).
4. **Tampoco se comprueba `minParticipants`** al reservar. Es un dato informativo.
5. **Precio:** `price` es por plaza y el importe cobrado es `price × participants` (`src/services/booking.service.ts:82`). La moneda no aparece en ningún sitio.
6. **Pago:** se cobra siempre al crear la reserva, y si sale bien el estado es siempre `paid` (`src/services/payment.service.ts:70`, `src/services/booking.service.ts:93`).
   - `PaymentStatus` se define como `'pending' | 'paid' | 'refunded'` (`src/types/payment.ts:4`), pero ningún código asigna `refunded`, y `pending` solo aparece como valor por defecto cuando falta el dato.
   - El cobro falla cuando el importe es múltiplo de 1000. Con los precios y las capacidades de los datos de ejemplo, en la práctica no se puede provocar el 402.
7. **"Estado de la reserva" para el CLI:** combina `paymentStatus` (en la práctica siempre `paid`) con `activity.status`, que viene en `GET /bookings`. Para mostrar si una actividad está confirmada, cancelado o hecho, hay que usar `activity.status`.
8. **Propiedad:** solo el dueño puede modificar, borrar o cambiar de estado una actividad (403 en caso contrario). Cada usuario solo ve sus propias reservas.
9. **Nada impide reservar actividades propias.** La spec dice lo contrario (`specs/feat-booking-creation.spec.md:34`), pero el código no lo comprueba.

---

## Discrepancias y dudas

1. **Posible fallo en el orden de inicialización (sacado del código y revisado a mano; sin confirmar con la API en marcha).**
   - `src/index.ts` importa los routers (`:5-8`) **antes** de llamar a `loadAllData()` (`:11`). Con `module: commonjs` (`tsconfig.json`), los `require` se ejecutan primero.
   - Al cargarse, los routers crean sus servicios con el repositorio compartido (`src/routes/auth.ts:11`, `src/routes/users.ts:11`, `src/routes/activities.ts:11`, `src/routes/bookings.ts:14-16`). En ese momento los repositorios todavía están vacíos.
   - Consecuencias:
     - (a) El `emailIndex` de `UserService` queda vacío (`src/services/user.service.ts:10-13`, `:50-56`), así que **`POST /login` con `m@f.c` / `1234aB` probablemente responda 401 "Invalid email or password"**.
     - (b) `nextId` empieza en 1 en todos los servicios. Un `POST /activities` o `POST /users` podría sobrescribir registros existentes (`activity-1`, `user-1`).
     - (c) `auth.ts` y `users.ts` usan **instancias distintas** de `UserService`, cada una con su propio `emailIndex`. Por eso un usuario recién registrado tampoco podría hacer login.
   - Alternativa para el cliente: `POST /users` ya devuelve `accessToken`, así que se puede trabajar con el token del registro.
2. **El README dice `termsAccepted` y el código exige `terms`** (`README.md:45` frente a `src/services/user.service.ts:167`).
3. **El README marca `duration` y `status` como obligatorios en `POST /activities`** (`README.md:56`), pero en el código son opcionales y tienen valor por defecto.
4. **El ciclo de vida de `README.md:10` y `AGENTS.md:6` está incompleto:** no recoge `sold-out` ni las transiciones `published→cancelled` y `sold-out→confirmed`. Lo que manda es el código.
5. **Los tipos de `client/` no coinciden con la API:** usan IDs numéricos, `Booking.date`, `payment.method` y `PaymentStatus 'none'`, mientras que el servidor usa IDs de texto, `createdAt` y `paymentStatus` (`client/booking.type.ts:5-28`). `client/d.json` es un juego de datos antiguo que el servidor no usa.
6. **FR7 (consultar disponibilidad) aparece como "NotStarted"** (`PRD.md:71-74`), así que no hay ningún endpoint para consultar las plazas libres.
7. **Borrar una actividad que tiene reservas** no está controlado. Después, `enrichBookingWithActivity` lanza `Activity not found` (`src/services/booking.service.ts:176-179`). Por inferencia, `GET /bookings` respondería **500** para todo el listado del usuario y `GET /bookings/:id` también respondería 500.
8. **Un JSON mal formado en el cuerpo** lo rechaza `express.json()` antes de llegar a las rutas. Probablemente responda 400 con el gestor de errores por defecto de Express (HTML), **no** con el formato `{message, errors}`. No está verificado.
9. **`q` repetido en la query** (`?q=a&q=b`) llega como array y `toLowerCase` fallaría, lo que daría 500. Es una inferencia.
10. **Concurrencia:** el cálculo de capacidad y la escritura de la reserva no son atómicos entre procesos. Como es un único proceso síncrono de Node, no debería haber sobreventa en una sola instancia. Es una inferencia.
11. **Cuando falla el pago se gasta igualmente un número de reserva** (`booking-${this.nextId++}` se ejecuta antes de cobrar, `src/services/booking.service.ts:83-90`), así que puede haber saltos en los IDs.
12. **`.gitignore` no excluye `db/*.json`**, de modo que los datos que se escriben al usar la API modifican ficheros versionados.
13. **`AGENTS.md:34` menciona `npm test` con Playwright,** pero en `package.json` no hay script `test` y no existe la carpeta `tests/`.
