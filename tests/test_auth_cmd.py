import json
import stat
import sys
from pathlib import Path

import httpx
import pytest
import respx
from jwt_helpers import make_jwt
from typer.testing import CliRunner, Result

from activity_bookings.cli import app
from activity_bookings.config import DEFAULT_API_URL, default_config_path
from activity_bookings.session import default_session_path

USERS_URL = f"{DEFAULT_API_URL}/users"
REGISTER_OK = {
    "user": {"id": 2, "username": "Ana", "email": "ana@example.com", "terms": True},
    "accessToken": "tok-123",
}
FULL_ARGS = ["auth", "register", "--username", "Ana", "--email", "ana@example.com"]
PASSWORDS = "secret1\nsecret1\n"
CUSTOM_API_URL = "http://api.example.com"


def run_register(runner: CliRunner, *extra: str, input: str = PASSWORDS + "y\n") -> Result:
    return runner.invoke(app, [*FULL_ARGS, *extra], input=input)


def sent_body(route: respx.Route) -> object:
    return json.loads(route.calls.last.request.content)


def configure_api_url(url: str) -> None:
    config = default_config_path()
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'api_url = "{url}"\n', encoding="utf-8")


def write_session(token: str) -> Path:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"access_token": token}), encoding="utf-8")
    return path


def assert_clean_failure(result: Result) -> None:
    assert result.exit_code == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.output


# --- help ----------------------------------------------------------------------------


def test_root_help_lists_auth(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "auth" in result.stdout


def test_auth_help_lists_register(runner: CliRunner) -> None:
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "register" in result.stdout


def test_auth_without_subcommand_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["auth"])
    assert "register" in result.output


# --- input ---------------------------------------------------------------------------


def test_register_sends_request_to_configured_api(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    configure_api_url(CUSTOM_API_URL)
    route = respx_mock.post(f"{CUSTOM_API_URL}/users").respond(201, json=REGISTER_OK)

    result = run_register(runner, "--accept-terms", input=PASSWORDS)

    assert result.exit_code == 0
    assert sent_body(route) == {
        "username": "Ana",
        "email": "ana@example.com",
        "password": "secret1",
        "terms": True,
    }


def test_register_prompts_for_missing_data(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = runner.invoke(
        app,
        ["auth", "register", "--accept-terms"],
        input="Ana\nana@example.com\n" + PASSWORDS,
    )
    assert result.exit_code == 0
    body = sent_body(route)
    assert isinstance(body, dict)
    assert (body["username"], body["email"], body["password"]) == (
        "Ana",
        "ana@example.com",
        "secret1",
    )


def test_register_mismatched_confirmation_asks_again(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = run_register(runner, "--accept-terms", input="secret1\nsecret2\n" + PASSWORDS)
    assert result.exit_code == 0
    assert result.output.count("Password") >= 2
    assert route.call_count == 1
    body = sent_body(route)
    assert isinstance(body, dict)
    assert body["password"] == "secret1"


def test_register_has_no_password_option(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, [*FULL_ARGS, "--password", "secret1"])
    assert result.exit_code == 2
    assert "No such option" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_register_terms_accepted_in_prompt(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = run_register(runner, input=PASSWORDS + "y\n")
    assert result.exit_code == 0
    body = sent_body(route)
    assert isinstance(body, dict)
    assert body["terms"] is True


def test_register_terms_rejected(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = run_register(runner, input=PASSWORDS + "n\n")
    assert_clean_failure(result)
    assert "accept the terms" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_register_invalid_config(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    config = default_config_path()
    config.parent.mkdir(parents=True)
    config.write_text('api_url = "ftp://example.com"\n', encoding="utf-8")

    result = runner.invoke(app, ["auth", "register"])

    assert_clean_failure(result)
    assert result.stderr.startswith("Error:")
    assert "api_url" in result.stderr
    assert "Username" not in result.output
    assert respx_mock.calls.call_count == 0


# --- success -------------------------------------------------------------------------


def test_register_success_output(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = run_register(runner)
    assert result.exit_code == 0
    assert "Account created for Ana (ana@example.com)." in result.stdout
    assert f"Logged in. Session saved to {default_session_path()}" in result.stdout
    assert "tok-123" not in result.output
    assert "secret1" not in result.output


def test_register_saves_session(
    runner: CliRunner, respx_mock: respx.MockRouter, isolated_env: Path
) -> None:
    configure_api_url(CUSTOM_API_URL)
    respx_mock.post(f"{CUSTOM_API_URL}/users").respond(201, json=REGISTER_OK)
    result = run_register(runner)
    assert result.exit_code == 0
    content = default_session_path().read_text(encoding="utf-8")
    assert json.loads(content) == {
        "api_url": CUSTOM_API_URL,
        "access_token": "tok-123",
        "user": {"id": 2, "username": "Ana", "email": "ana@example.com"},
    }
    assert "secret1" not in content


def test_register_session_without_xdg(
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    isolated_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME")
    respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = run_register(runner)
    assert result.exit_code == 0
    assert (isolated_env / ".config" / "activity-bookings" / "session.json").is_file()


def test_register_session_with_xdg(
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    result = run_register(runner)
    assert result.exit_code == 0
    assert (tmp_path / "cfg" / "activity-bookings" / "session.json").is_file()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_register_session_permissions(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)
    assert run_register(runner).exit_code == 0
    assert stat.S_IMODE(default_session_path().stat().st_mode) == 0o600


def test_register_replaces_previous_session(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    path = write_session("old-token")
    respx_mock.post(USERS_URL).respond(201, json={**REGISTER_OK, "accessToken": "new-token"})
    assert run_register(runner).exit_code == 0
    content = path.read_text(encoding="utf-8")
    assert "new-token" in content
    assert "old-token" not in content


# --- errors --------------------------------------------------------------------------


def test_register_validation_errors(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(
        400,
        json={
            "message": "Validation failed",
            "errors": [
                {"field": "email", "message": "Email must be valid"},
                {"field": "password", "message": "Password must be at least 6 characters"},
            ],
        },
    )
    result = run_register(runner)
    assert_clean_failure(result)
    assert "Error: Validation failed" in result.stderr
    assert "email: Email must be valid" in result.stderr
    assert "password: Password must be at least 6 characters" in result.stderr
    assert not default_session_path().exists()


def test_register_email_already_registered(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    message = "Email is already registered"
    respx_mock.post(USERS_URL).respond(
        400, json={"message": message, "errors": [{"field": "email", "message": message}]}
    )
    result = run_register(runner)
    assert_clean_failure(result)
    assert f"Error: {message}" in result.stderr


def test_register_error_without_fields(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(
        400, json={"message": "Failed to register user", "errors": []}
    )
    result = run_register(runner)
    assert_clean_failure(result)
    assert "Error: Failed to register user" in result.stderr


def test_register_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = run_register(runner)
    assert_clean_failure(result)
    assert f"cannot connect to the API at {DEFAULT_API_URL}" in result.stderr
    assert not default_session_path().exists()


def test_register_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = run_register(runner)
    assert_clean_failure(result)
    assert "did not respond in time" in result.stderr


def test_register_server_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(500, json={"message": "Internal server error", "errors": []})
    result = run_register(runner)
    assert_clean_failure(result)
    assert "500" in result.stderr
    assert "Internal server error" in result.stderr


def test_register_non_json_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(400, html="<html><body>Bad Request</body></html>")
    result = run_register(runner)
    assert_clean_failure(result)
    assert "400" in result.stderr


def test_register_success_without_token(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(USERS_URL).respond(201, json={"user": {"id": 2}})
    result = run_register(runner)
    assert_clean_failure(result)
    assert "invalid response from the API" in result.stderr
    assert not default_session_path().exists()


def test_register_failure_keeps_previous_session(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    path = write_session("old-token")
    respx_mock.post(USERS_URL).respond(
        400, json={"message": "Failed to register user", "errors": []}
    )
    assert_clean_failure(run_register(runner))
    assert "old-token" in path.read_text(encoding="utf-8")


def test_register_session_save_failure(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    session_dir = default_session_path().parent
    session_dir.parent.mkdir(parents=True)
    session_dir.write_text("not a directory", encoding="utf-8")
    respx_mock.post(USERS_URL).respond(201, json=REGISTER_OK)

    result = run_register(runner)

    assert_clean_failure(result)
    assert "account created" in result.stderr
    assert "could not be saved" in result.stderr
    assert str(default_session_path()) in result.stderr


# === auth login ======================================================================

LOGIN_URL = f"{DEFAULT_API_URL}/login"
LOGIN_OK = {
    "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c", "terms": True},
    "accessToken": "tok-123",
}


def run_login(runner: CliRunner, *args: str, input: str = "1234aB\n") -> Result:
    return runner.invoke(app, ["auth", "login", "--email", "m@f.c", *args], input=input)


def test_auth_help_lists_login_logout_whoami(runner: CliRunner) -> None:
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    for name in ("login", "logout", "whoami"):
        assert name in result.stdout


def test_login_sends_request_to_configured_api(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    configure_api_url(CUSTOM_API_URL)
    route = respx_mock.post(f"{CUSTOM_API_URL}/login").respond(200, json=LOGIN_OK)
    result = run_login(runner)
    assert result.exit_code == 0
    assert sent_body(route) == {"email": "m@f.c", "password": "1234aB"}


def test_login_prompts_for_email(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(LOGIN_URL).respond(200, json=LOGIN_OK)
    result = runner.invoke(app, ["auth", "login"], input="m@f.c\n1234aB\n")
    assert result.exit_code == 0
    assert sent_body(route) == {"email": "m@f.c", "password": "1234aB"}


def test_login_success_output(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(LOGIN_URL).respond(200, json=LOGIN_OK)
    result = run_login(runner)
    assert result.exit_code == 0
    assert "Logged in as Mark Musk (m@f.c)." in result.stdout
    assert f"Session saved to {default_session_path()}" in result.stdout
    assert "1234aB" not in result.output
    assert "tok-123" not in result.output


def test_login_has_no_password_option(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["auth", "login", "--password", "1234aB"])
    assert result.exit_code == 2
    assert "No such option" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_login_invalid_config(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    configure_api_url("ftp://example.com")
    result = runner.invoke(app, ["auth", "login", "--email", "m@f.c"])
    assert_clean_failure(result)
    assert result.stderr.startswith("Error:")
    assert "api_url" in result.stderr
    assert "Password" not in result.output
    assert respx_mock.calls.call_count == 0


def test_login_saves_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    configure_api_url(CUSTOM_API_URL)
    respx_mock.post(f"{CUSTOM_API_URL}/login").respond(200, json=LOGIN_OK)
    assert run_login(runner).exit_code == 0
    path = default_session_path()
    content = path.read_text(encoding="utf-8")
    assert json.loads(content) == {
        "api_url": CUSTOM_API_URL,
        "access_token": "tok-123",
        "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"},
    }
    assert "1234aB" not in content
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_login_replaces_previous_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    path = write_session("old-token")
    respx_mock.post(LOGIN_URL).respond(200, json={**LOGIN_OK, "accessToken": "new-token"})
    assert run_login(runner).exit_code == 0
    content = path.read_text(encoding="utf-8")
    assert "new-token" in content
    assert "old-token" not in content


@pytest.mark.parametrize("message", ["Invalid email or password", "Authentication failed"])
def test_login_rejected(runner: CliRunner, respx_mock: respx.MockRouter, message: str) -> None:
    respx_mock.post(LOGIN_URL).respond(401, json={"message": message, "errors": []})
    result = run_login(runner)
    assert_clean_failure(result)
    assert f"Error: {message}" in result.stderr
    assert not default_session_path().exists()


def test_login_rejected_keeps_previous_session(
    runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    path = write_session("old-token")
    respx_mock.post(LOGIN_URL).respond(
        401, json={"message": "Invalid email or password", "errors": []}
    )
    assert_clean_failure(run_login(runner))
    assert "old-token" in path.read_text(encoding="utf-8")


def test_login_empty_email(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    message = "Email is required and must be a non-empty string"
    route = respx_mock.post(LOGIN_URL).respond(
        400,
        json={"message": "Validation failed", "errors": [{"field": "email", "message": message}]},
    )
    result = runner.invoke(app, ["auth", "login", "--email", ""], input="1234aB\n")
    assert_clean_failure(result)
    assert sent_body(route) == {"email": "", "password": "1234aB"}
    assert "Error: Validation failed" in result.stderr
    assert f"email: {message}" in result.stderr


def test_login_api_down(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(LOGIN_URL).mock(side_effect=httpx.ConnectError("refused"))
    result = run_login(runner)
    assert_clean_failure(result)
    assert f"cannot connect to the API at {DEFAULT_API_URL}" in result.stderr


def test_login_timeout(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(LOGIN_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    result = run_login(runner)
    assert_clean_failure(result)
    assert "did not respond in time" in result.stderr


def test_login_server_error(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(LOGIN_URL).respond(500, json={"message": "Internal server error", "errors": []})
    result = run_login(runner)
    assert_clean_failure(result)
    assert "500" in result.stderr
    assert "Internal server error" in result.stderr


def test_login_success_without_token(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(LOGIN_URL).respond(200, json={"user": {"id": 1}})
    result = run_login(runner)
    assert_clean_failure(result)
    assert "invalid response from the API" in result.stderr
    assert not default_session_path().exists()


def test_login_session_save_failure(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    session_dir = default_session_path().parent
    session_dir.parent.mkdir(parents=True)
    session_dir.write_text("not a directory", encoding="utf-8")
    respx_mock.post(LOGIN_URL).respond(200, json=LOGIN_OK)

    result = run_login(runner)

    assert_clean_failure(result)
    assert "logged in, but" in result.stderr
    assert "could not be saved" in result.stderr
    assert str(default_session_path()) in result.stderr


# === auth logout =====================================================================


def write_valid_session(token: str = "tok-123", api_url: str = CUSTOM_API_URL) -> Path:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "api_url": api_url,
        "access_token": token,
        "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"},
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_raw_session(content: str) -> Path:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_logout_with_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    path = write_valid_session()
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    assert f"Logged out. Session removed from {path}" in result.stdout
    assert not path.exists()
    assert respx_mock.calls.call_count == 0


def test_logout_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    assert "Not logged in." in result.stdout
    assert respx_mock.calls.call_count == 0


def test_logout_with_corrupt_session(runner: CliRunner) -> None:
    path = write_raw_session("not json")
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    assert not path.exists()


def test_logout_failure(runner: CliRunner) -> None:
    path = default_session_path()
    path.mkdir(parents=True)
    result = runner.invoke(app, ["auth", "logout"])
    assert_clean_failure(result)
    assert str(path) in result.stderr


# === auth whoami =====================================================================

EXP_2100 = 4102444800  # 2100-01-01 00:00 UTC
EXP_2000 = 946684800  # 2000-01-01 00:00 UTC


def test_whoami_valid_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    token = make_jwt(EXP_2100)
    write_valid_session(token)
    result = runner.invoke(app, ["auth", "whoami"])
    assert result.exit_code == 0
    for text in ("Mark Musk", "m@f.c", CUSTOM_API_URL, "2100-01-01 00:00 UTC"):
        assert text in result.stdout
    assert "expired" not in result.stdout
    assert token not in result.output
    assert respx_mock.calls.call_count == 0


def test_whoami_expired_token(runner: CliRunner) -> None:
    write_valid_session(make_jwt(EXP_2000))
    result = runner.invoke(app, ["auth", "whoami"])
    assert result.exit_code == 0
    assert "2000-01-01 00:00 UTC (expired)" in result.stdout
    assert "activity-bookings auth login" in result.stdout


def test_whoami_unreadable_expiry(runner: CliRunner) -> None:
    write_valid_session("tok-123")
    result = runner.invoke(app, ["auth", "whoami"])
    assert result.exit_code == 0
    assert "unknown" in result.stdout
    assert "tok-123" not in result.output


def test_whoami_without_session(runner: CliRunner, respx_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["auth", "whoami"])
    assert_clean_failure(result)
    assert "not logged in" in result.stderr
    assert "activity-bookings auth login" in result.stderr
    assert respx_mock.calls.call_count == 0


def test_whoami_not_json(runner: CliRunner) -> None:
    path = write_raw_session("not json")
    result = runner.invoke(app, ["auth", "whoami"])
    assert_clean_failure(result)
    assert str(path) in result.stderr
    assert "activity-bookings auth login" in result.stderr


def test_whoami_session_without_token(runner: CliRunner) -> None:
    path = write_raw_session(
        '{"api_url": "http://localhost:3000",'
        ' "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"}}'
    )
    result = runner.invoke(app, ["auth", "whoami"])
    assert_clean_failure(result)
    assert str(path) in result.stderr
