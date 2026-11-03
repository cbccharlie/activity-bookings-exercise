"""HTTP client for the ActivityBookings API: requests, response models and error translation."""

from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self

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


def _require_str(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ApiResponseError(f"invalid response from the API: missing or invalid '{label}'")
    return value


class ApiClient:
    """Synchronous client for the ActivityBookings API. Use it as a context manager."""

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

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

    def _request(self, method: str, path: str, json: object = None) -> object:
        """Send a request and return the decoded JSON body, translating every failure."""
        try:
            response = self._http.request(method, path, json=json)
        except httpx.ConnectError as exc:
            raise ApiConnectionError(f"cannot connect to the API at {self.base_url}") from exc
        except httpx.TimeoutException as exc:
            raise ApiConnectionError(f"the API at {self.base_url} did not respond in time") from exc
        except httpx.HTTPError as exc:
            raise ApiConnectionError(f"request to the API failed: {exc}") from exc

        if response.is_error:
            raise _api_error(response)
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
