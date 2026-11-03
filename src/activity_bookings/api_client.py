"""HTTP client for the ActivityBookings API: requests, response models and error translation."""

from dataclasses import dataclass, fields
from types import TracebackType
from typing import Any, Self
from urllib.parse import quote

import httpx

from activity_bookings.errors import (
    ApiConnectionError,
    ApiError,
    ApiResponseError,
    FieldError,
)

DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True)
class User:
    """A user as returned by the API. `id` is numeric for `POST /users`, text elsewhere."""

    id: int | str
    username: str
    email: str


@dataclass(frozen=True)
class AuthResult:
    """The authenticated user and the JWT that identifies them."""

    user: User
    access_token: str


def parse_user(data: object) -> User:
    """Build a User from an API JSON object, raising ApiResponseError if it is malformed."""
    if not isinstance(data, dict):
        raise ApiResponseError("invalid response from the API: 'user' is not an object")
    user_id = data.get("id")
    if isinstance(user_id, bool) or not isinstance(user_id, int | str):
        raise ApiResponseError("invalid response from the API: missing or invalid 'user.id'")
    username = _require_str(data, "username", "user.username")
    email = _require_str(data, "email", "user.email")
    return User(id=user_id, username=username, email=email)


def parse_auth_result(data: object) -> AuthResult:
    """Build an AuthResult from `{"user": {...}, "accessToken": "..."}`."""
    if not isinstance(data, dict):
        raise ApiResponseError("invalid response from the API: body is not a JSON object")
    if "user" not in data:
        raise ApiResponseError("invalid response from the API: missing 'user'")
    user = parse_user(data["user"])
    access_token = _require_str(data, "accessToken", "accessToken")
    return AuthResult(user=user, access_token=access_token)


@dataclass(frozen=True)
class Activity:
    """An activity as listed by the API. Only the fields the CLI shows are modelled."""

    id: str
    name: str
    date: str
    location: str
    price: float
    max_participants: int
    status: str


def parse_activity(data: object, position: int | None = None) -> Activity:
    """Build an Activity from an API JSON object, raising ApiResponseError if it is malformed.

    The error names the activity by its id or, if that is not valid, by `position`.
    """
    label = "activity" if position is None else f"activity at position {position}"
    if not isinstance(data, dict):
        raise ApiResponseError(f"invalid response from the API: {label} is not an object")
    raw_id = data.get("id")
    if isinstance(raw_id, str) and raw_id:
        label = f"activity {raw_id}"

    def invalid(field: str) -> ApiResponseError:
        return ApiResponseError(f"invalid response from the API: {label} has no valid '{field}'")

    price = data.get("price")
    if isinstance(price, bool) or not isinstance(price, int | float):
        raise invalid("price")
    max_participants = data.get("maxParticipants")
    if isinstance(max_participants, bool) or not isinstance(max_participants, int):
        raise invalid("maxParticipants")

    fields: dict[str, str] = {}
    for key in ("id", "name", "date", "location", "status"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise invalid(key)
        fields[key] = value
    return Activity(
        id=fields["id"],
        name=fields["name"],
        date=fields["date"],
        location=fields["location"],
        price=float(price),
        max_participants=max_participants,
        status=fields["status"],
    )


@dataclass(frozen=True)
class ActivityDetail:
    """An activity as returned by `GET /activities/:id`: the listed fields plus the detail."""

    activity: Activity
    slug: str
    duration: int
    min_participants: int
    user_id: str
    created_at: str
    updated_at: str | None


def parse_activity_detail(data: object) -> ActivityDetail:
    """Build an ActivityDetail from an API JSON object, raising ApiResponseError if malformed."""
    if not isinstance(data, dict):
        raise ApiResponseError("invalid response from the API: expected an activity")
    activity = parse_activity(data)

    def invalid(field: str) -> ApiResponseError:
        return ApiResponseError(
            f"invalid response from the API: activity {activity.id} has no valid '{field}'"
        )

    def whole_number(key: str) -> int:
        value = data.get(key)
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, bool) or not isinstance(value, int):
            raise invalid(key)
        return value

    texts: dict[str, str] = {}
    for key in ("slug", "userId", "createdAt"):
        value = data.get(key)
        if not isinstance(value, str):
            raise invalid(key)
        texts[key] = value
    updated_at = data.get("updatedAt")
    if updated_at is not None and not isinstance(updated_at, str):
        raise invalid("updatedAt")
    return ActivityDetail(
        activity=activity,
        slug=texts["slug"],
        duration=whole_number("duration"),
        min_participants=whole_number("minParticipants"),
        user_id=texts["userId"],
        created_at=texts["createdAt"],
        updated_at=updated_at,
    )


@dataclass(frozen=True)
class Booking:
    """A booking as returned by `POST /bookings`. The amount charged is not returned."""

    id: str
    activity_id: str
    user_id: str
    participants: int
    created_at: str
    payment_status: str


def parse_booking(data: object, label: str = "booking") -> Booking:
    """Build a Booking from an API JSON object, raising ApiResponseError if it is malformed.

    A missing `paymentStatus` means `pending`, as the API does in `GET /bookings`.
    `label` names the booking in error messages.
    """
    if not isinstance(data, dict):
        raise ApiResponseError(f"invalid response from the API: {label} is not an object")

    def invalid(field: str) -> ApiResponseError:
        return ApiResponseError(f"invalid response from the API: {label} has no valid '{field}'")

    texts: dict[str, str] = {}
    for key in ("id", "activityId", "userId", "createdAt"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise invalid(key)
        texts[key] = value

    participants = data.get("participants")
    if isinstance(participants, float) and participants.is_integer():
        participants = int(participants)
    if isinstance(participants, bool) or not isinstance(participants, int):
        raise invalid("participants")

    payment_status = data.get("paymentStatus", "pending")
    if not isinstance(payment_status, str) or not payment_status:
        raise invalid("paymentStatus")

    return Booking(
        id=texts["id"],
        activity_id=texts["activityId"],
        user_id=texts["userId"],
        participants=participants,
        created_at=texts["createdAt"],
        payment_status=payment_status,
    )


@dataclass(frozen=True)
class BookingActivity:
    """The activity embedded in a `GET /bookings` item. Only the fields the CLI shows."""

    name: str
    date: str
    price: float
    status: str


@dataclass(frozen=True)
class BookingSummary:
    """A booking as listed by `GET /bookings`: the booking and its activity."""

    booking: Booking
    activity: BookingActivity


def parse_booking_summary(data: object, position: int | None = None) -> BookingSummary:
    """Build a BookingSummary from a `GET /bookings` item, raising ApiResponseError if malformed.

    The error names the booking by its id or, if that is not valid, by `position`.
    """
    label = "booking" if position is None else f"booking at position {position}"
    if not isinstance(data, dict):
        raise ApiResponseError(f"invalid response from the API: {label} is not an object")
    raw_id = data.get("id")
    if isinstance(raw_id, str) and raw_id:
        label = f"booking {raw_id}"
    booking = parse_booking(data, label)

    def invalid(field: str) -> ApiResponseError:
        return ApiResponseError(f"invalid response from the API: {label} has no valid '{field}'")

    raw = data.get("activity")
    if not isinstance(raw, dict):
        raise invalid("activity")
    price = raw.get("price")
    if isinstance(price, bool) or not isinstance(price, int | float):
        raise invalid("activity.price")
    texts: dict[str, str] = {}
    for key in ("name", "date", "status"):
        value = raw.get(key)
        if not isinstance(value, str) or not value:
            raise invalid(f"activity.{key}")
        texts[key] = value
    activity = BookingActivity(
        name=texts["name"], date=texts["date"], price=float(price), status=texts["status"]
    )
    return BookingSummary(booking=booking, activity=activity)


_JSON_KEYS = {"min_participants": "minParticipants", "max_participants": "maxParticipants"}


@dataclass(frozen=True)
class NewActivity:
    """Data for `POST /activities`. `duration` (minutes) is sent only if given."""

    name: str
    price: float
    date: str
    location: str
    min_participants: int
    max_participants: int
    duration: int | None = None

    def to_json(self) -> dict[str, object]:
        """Return the request body; there is no `status`, so the API default applies."""
        return _activity_body(self)


@dataclass(frozen=True)
class ActivityChanges:
    """Fields to change with `PUT /activities/:id`; `None` means unchanged."""

    name: str | None = None
    price: float | None = None
    date: str | None = None
    location: str | None = None
    min_participants: int | None = None
    max_participants: int | None = None
    duration: int | None = None

    def to_json(self) -> dict[str, object]:
        """Return the request body with only the fields that change."""
        return _activity_body(self)

    def is_empty(self) -> bool:
        """Return True if no field changes."""
        return not self.to_json()


def _activity_body(data: NewActivity | ActivityChanges) -> dict[str, object]:
    """Serialise the non-None fields of `data` with the API's camelCase keys."""
    body: dict[str, object] = {}
    for field in fields(data):
        value = getattr(data, field.name)
        if value is not None:
            body[_JSON_KEYS.get(field.name, field.name)] = value
    return body


def _activity_path(activity_id: str) -> str:
    return f"/activities/{quote(activity_id, safe='')}"


def _require_str(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ApiResponseError(f"invalid response from the API: missing or invalid '{label}'")
    return value


class ApiClient:
    """Synchronous client for the ActivityBookings API. Use it as a context manager."""

    def __init__(
        self, base_url: str, timeout: float = DEFAULT_TIMEOUT, token: str | None = None
    ) -> None:
        """Create the client; with `token`, every request carries `Authorization: Bearer`."""
        self.base_url = base_url
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        self._http = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying HTTP connections."""
        self._http.close()

    def register(self, username: str, email: str, password: str) -> AuthResult:
        """Create an account with `POST /users` (terms accepted) and return its token."""
        body = {"username": username, "email": email, "password": password, "terms": True}
        return parse_auth_result(self._request("POST", "/users", json=body))

    def login(self, email: str, password: str) -> AuthResult:
        """Log in with `POST /login` and return the user and its token."""
        body = {"email": email, "password": password}
        return parse_auth_result(self._request("POST", "/login", json=body))

    def list_activities(
        self, search: str | None = None, sort: str | None = None, order: str = "asc"
    ) -> list[Activity]:
        """List activities with `GET /activities`, optionally searched and sorted by the API.

        `q` is sent only with `search`; `_sort` and `_order` only with `sort`.
        """
        params: dict[str, str] = {}
        if search is not None:
            params["q"] = search
        if sort is not None:
            params["_sort"] = sort
            params["_order"] = order
        data = self._request("GET", "/activities", params=params)
        if not isinstance(data, list):
            raise ApiResponseError("invalid response from the API: expected a list of activities")
        return [parse_activity(item, position) for position, item in enumerate(data, start=1)]

    def get_activity(self, activity_id: str) -> ActivityDetail:
        """Get one activity with `GET /activities/<id>` (public, no token needed)."""
        return parse_activity_detail(self._request("GET", _activity_path(activity_id)))

    def create_activity(self, activity: NewActivity) -> Activity:
        """Create an activity with `POST /activities` (requires a token) and return it."""
        return parse_activity(self._request("POST", "/activities", json=activity.to_json()))

    def update_activity(self, activity_id: str, changes: ActivityChanges) -> Activity:
        """Change an activity with `PUT /activities/<id>` (requires a token) and return it."""
        data = self._request("PUT", _activity_path(activity_id), json=changes.to_json())
        return parse_activity(data)

    def delete_activity(self, activity_id: str) -> None:
        """Delete an activity with `DELETE /activities/<id>` (requires a token)."""
        self._request("DELETE", _activity_path(activity_id), expect_body=False)

    def create_booking(self, activity_id: str, participants: int) -> Booking:
        """Book seats with `POST /bookings` (requires a token); the API charges at once."""
        body = {"activityId": activity_id, "participants": participants}
        return parse_booking(self._request("POST", "/bookings", json=body))

    def list_bookings(self, activity_id: str | None = None) -> list[BookingSummary]:
        """List the token's bookings with `GET /bookings`, optionally for one activity.

        `activityId` is sent only with `activity_id`.
        """
        params = {} if activity_id is None else {"activityId": activity_id}
        data = self._request("GET", "/bookings", params=params)
        if not isinstance(data, list):
            raise ApiResponseError("invalid response from the API: expected a list of bookings")
        return [
            parse_booking_summary(item, position) for position, item in enumerate(data, start=1)
        ]

    def _request(
        self,
        method: str,
        path: str,
        json: object = None,
        params: dict[str, str] | None = None,
        expect_body: bool = True,
    ) -> object:
        """Send a request and return the decoded JSON body, translating every failure.

        With `expect_body=False` the body of a successful response is ignored (e.g. 204).
        """
        try:
            response = self._http.request(method, path, json=json, params=params)
        except httpx.ConnectError as exc:
            raise ApiConnectionError(f"cannot connect to the API at {self.base_url}") from exc
        except httpx.TimeoutException as exc:
            raise ApiConnectionError(f"the API at {self.base_url} did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise ApiConnectionError(f"request to the API failed: {exc}") from exc

        if response.is_error:
            raise _api_error(response)
        if not expect_body:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ApiResponseError("invalid response from the API: body is not JSON") from exc


def _api_error(response: httpx.Response) -> ApiError:
    """Translate an error response (`{message, errors}` or anything else) into ApiError."""
    status = response.status_code
    unexpected = ApiError(status, f"API returned HTTP {status} with an unexpected response")
    try:
        data = response.json()
    except ValueError:
        return unexpected
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        return unexpected

    message: str = data["message"]
    if status >= 500:
        return ApiError(status, f"API error {status}: {message}")
    return ApiError(status, message, _field_errors(data.get("errors")))


def _field_errors(raw: object) -> tuple[FieldError, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        FieldError(field=item["field"], message=item["message"])
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("field"), str)
        and isinstance(item.get("message"), str)
    )
