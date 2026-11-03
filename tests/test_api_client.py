import json

import httpx
import pytest
import respx

from activity_bookings.api_client import (
    ApiClient,
    AuthResult,
    User,
    parse_auth_result,
)
from activity_bookings.errors import (
    ApiConnectionError,
    ApiError,
    ApiResponseError,
    FieldError,
)

BASE_URL = "http://api.example.com"
REGISTER_OK = {
    "user": {"id": 2, "username": "Ana", "email": "ana@example.com", "terms": True},
    "accessToken": "tok-123",
}


# --- ApiError text -------------------------------------------------------------------


def test_api_error_without_field_errors() -> None:
    error = ApiError(400, "Failed to register user")
    assert str(error) == "Failed to register user"
    assert error.status_code == 400
    assert error.field_errors == ()


def test_api_error_with_field_errors() -> None:
    error = ApiError(
        400,
        "Validation failed",
        (FieldError("email", "Email must be valid"), FieldError("password", "Too short")),
    )
    assert str(error) == (
        "Validation failed\n  - email: Email must be valid\n  - password: Too short"
    )
    assert error.message == "Validation failed"


# --- parsing -------------------------------------------------------------------------


def test_parse_valid_response() -> None:
    assert parse_auth_result(REGISTER_OK) == AuthResult(
        user=User(id=2, username="Ana", email="ana@example.com"), access_token="tok-123"
    )


def test_parse_text_id() -> None:
    data = {"user": {"id": "user-2", "username": "Ana", "email": "a@b.c"}, "accessToken": "t"}
    assert parse_auth_result(data).user.id == "user-2"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"user": {"id": 2}}, "user.username"),
        ({"user": {"id": 2, "username": "Ana", "email": "a@b.c"}}, "accessToken"),
        ({"accessToken": "tok"}, "'user'"),
        ({"user": "Ana", "accessToken": "tok"}, "'user' is not an object"),
        ({"user": {"username": "Ana", "email": "a@b.c"}, "accessToken": "t"}, "user.id"),
        ({"user": {"id": True, "username": "A", "email": "a@b.c"}, "accessToken": "t"}, "user.id"),
        ({"user": {"id": 2, "username": "Ana", "email": "a@b.c"}, "accessToken": 3}, "accessToken"),
        ([], "not a JSON object"),
    ],
)
def test_parse_incomplete_response(data: object, expected: str) -> None:
    with pytest.raises(ApiResponseError, match="invalid response from the API") as exc:
        parse_auth_result(data)
    assert expected in str(exc.value)


# --- ApiClient.register --------------------------------------------------------------


def register(base_url: str = BASE_URL) -> AuthResult:
    with ApiClient(base_url) as client:
        return client.register("Ana", "ana@example.com", "secret1")


def test_register_sends_body_and_parses_result(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(f"{BASE_URL}/users").respond(201, json=REGISTER_OK)
    result = register()
    assert result.access_token == "tok-123"
    assert result.user == User(id=2, username="Ana", email="ana@example.com")
    assert json.loads(route.calls.last.request.content) == {
        "username": "Ana",
        "email": "ana@example.com",
        "password": "secret1",
        "terms": True,
    }


def test_register_validation_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [
                {"field": "email", "message": "Email must be valid"},
                {"field": "password", "message": "Password must be at least 6 characters"},
            ],
        },
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert exc.value.status_code == 400
    assert exc.value.field_errors == (
        FieldError("email", "Email must be valid"),
        FieldError("password", "Password must be at least 6 characters"),
    )


def test_register_error_without_fields(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        400, json={"message": "Failed to register user", "errors": []}
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert str(exc.value) == "Failed to register user"


def test_register_server_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(
        500, json={"message": "Internal server error", "errors": []}
    )
    with pytest.raises(ApiError) as exc:
        register()
    assert exc.value.status_code == 500
    assert str(exc.value) == "API error 500: Internal server error"


@pytest.mark.parametrize("status", [400, 502])
def test_register_non_json_error(respx_mock: respx.MockRouter, status: int) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(status, html="<pre>Bad Request</pre>")
    with pytest.raises(ApiError) as exc:
        register()
    assert str(exc.value) == f"API returned HTTP {status} with an unexpected response"


def test_register_json_error_without_message(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(400, json={"error": "nope"})
    with pytest.raises(ApiError, match="unexpected response"):
        register()


def test_register_connection_refused(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ApiConnectionError, match=f"cannot connect to the API at {BASE_URL}"):
        register()


def test_register_timeout(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ApiConnectionError, match="did not respond in time"):
        register()


def test_register_other_transport_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").mock(side_effect=httpx.RemoteProtocolError("boom"))
    with pytest.raises(ApiConnectionError, match="request to the API failed: boom"):
        register()


def test_register_success_without_json(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(201, text="created")
    with pytest.raises(ApiResponseError, match="not JSON"):
        register()


def test_register_success_without_token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/users").respond(201, json={"user": {"id": 2}})
    with pytest.raises(ApiResponseError):
        register()
