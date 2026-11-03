import json
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jwt_helpers import make_jwt

from activity_bookings import session as session_module
from activity_bookings.api_client import User
from activity_bookings.errors import SessionError
from activity_bookings.session import (
    Session,
    default_session_path,
    delete_session,
    load_session,
    require_session,
    save_session,
    token_expiry,
)

SESSION = Session(
    api_url="http://api.example.com",
    access_token="tok-123",
    user=User(id=2, username="Ana", email="ana@example.com"),
)


def test_default_path_without_xdg(isolated_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert default_session_path() == isolated_env / ".config" / "activity-bookings" / "session.json"


def test_default_path_with_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    assert default_session_path() == tmp_path / "cfg" / "activity-bookings" / "session.json"


def test_save_creates_directory_and_content() -> None:
    assert not default_session_path().parent.exists()
    path = save_session(SESSION)
    assert path == default_session_path()
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "api_url": "http://api.example.com",
        "access_token": "tok-123",
        "user": {"id": 2, "username": "Ana", "email": "ana@example.com"},
    }


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_save_uses_private_permissions() -> None:
    path = save_session(SESSION)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_save_replaces_previous_session_and_fixes_permissions() -> None:
    path = default_session_path()
    path.parent.mkdir(parents=True)
    path.write_text('{"access_token": "old-token"}', encoding="utf-8")
    path.chmod(0o644)

    save_session(SESSION)

    content = path.read_text(encoding="utf-8")
    assert "tok-123" in content
    assert "old-token" not in content
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in path.parent.iterdir()] == ["session.json"]


def test_save_fails_when_directory_is_a_file() -> None:
    directory = default_session_path().parent
    directory.parent.mkdir(parents=True)
    directory.write_text("not a directory", encoding="utf-8")
    with pytest.raises(SessionError) as exc:
        save_session(SESSION)
    assert str(default_session_path()) in str(exc.value)


def write_raw_session(content: str) -> Path:
    path = default_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --- load_session --------------------------------------------------------------------


def test_load_round_trip() -> None:
    save_session(SESSION)
    assert load_session() == SESSION


def test_load_text_user_id() -> None:
    session = Session("http://x.example", "tok", User(id="user-1", username="A", email="a@b.c"))
    save_session(session)
    assert load_session() == session


def test_load_missing_file() -> None:
    assert load_session() is None


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("not json", "not valid JSON"),
        ("[]", "not a JSON object"),
        (
            '{"api_url": "http://localhost:3000",'
            ' "user": {"id": 1, "username": "Mark Musk", "email": "m@f.c"}}',
            "access_token",
        ),
        ('{"api_url": "http://localhost:3000", "access_token": "t"}', "'user'"),
        ('{"access_token": "t", "user": {"id": 1, "username": "A", "email": "a"}}', "api_url"),
    ],
)
def test_load_invalid_file(content: str, expected: str) -> None:
    path = write_raw_session(content)
    with pytest.raises(SessionError) as exc:
        load_session()
    message = str(exc.value)
    assert str(path) in message
    assert expected in message
    assert "activity-bookings auth login" in message


# --- delete_session ------------------------------------------------------------------


def test_delete_existing_session() -> None:
    path = save_session(SESSION)
    assert delete_session() is True
    assert not path.exists()


def test_delete_missing_session() -> None:
    assert delete_session() is False


def test_delete_corrupt_session() -> None:
    path = write_raw_session("not json")
    assert delete_session() is True
    assert not path.exists()


def test_delete_failure() -> None:
    path = default_session_path()
    path.mkdir(parents=True)
    with pytest.raises(SessionError) as exc:
        delete_session()
    assert str(path) in str(exc.value)


# --- token_expiry --------------------------------------------------------------------


def test_token_expiry_valid() -> None:
    assert token_expiry(make_jwt(4102444800)) == datetime(2100, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "token",
    [
        "tok-123",
        "a.b",
        "header.@@@.signature",
        "header.bm90IGpzb24.signature",  # base64url of "not json"
        make_jwt("tomorrow"),
        make_jwt(True),
        make_jwt(None),
        make_jwt(10**20),
    ],
)
def test_token_expiry_unreadable(token: str) -> None:
    assert token_expiry(token) is None


# --- require_session -----------------------------------------------------------------

EXP_2000 = 946684800
EXP_2100 = 4102444800


def save_with(api_url: str = "http://api.example.com", token: str = "tok-123") -> Session:
    session = Session(api_url=api_url, access_token=token, user=SESSION.user)
    save_session(session)
    return session


def test_require_session_without_session() -> None:
    with pytest.raises(SessionError, match="not logged in") as exc:
        require_session("http://api.example.com")
    assert "activity-bookings auth login" in str(exc.value)


def test_require_session_invalid_file_propagates() -> None:
    path = default_session_path()
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(SessionError, match="invalid session file") as exc:
        require_session("http://api.example.com")
    assert str(path) in str(exc.value)


def test_require_session_other_api_url() -> None:
    save_with(api_url="http://localhost:3000")
    with pytest.raises(SessionError) as exc:
        require_session("http://api.example.com")
    message = str(exc.value)
    assert "http://localhost:3000" in message
    assert "http://api.example.com" in message
    assert "activity-bookings auth login" in message


def test_require_session_trailing_slash_is_the_same_api() -> None:
    session = save_with(api_url="http://api.example.com/", token=make_jwt(EXP_2100))
    assert require_session("http://api.example.com") == session


def test_require_session_expired_token() -> None:
    save_with(token=make_jwt(EXP_2000))
    with pytest.raises(SessionError) as exc:
        require_session("http://api.example.com")
    message = str(exc.value)
    assert "expired on 2000-01-01 00:00 UTC" in message
    assert "activity-bookings auth login" in message


def test_require_session_valid_token() -> None:
    session = save_with(token=make_jwt(EXP_2100))
    assert require_session("http://api.example.com") == session


def test_require_session_uses_patchable_now(monkeypatch: pytest.MonkeyPatch) -> None:
    save_with(token=make_jwt(EXP_2100))
    monkeypatch.setattr(session_module, "_now", lambda: datetime(2101, 1, 1, tzinfo=UTC))
    with pytest.raises(SessionError, match="expired"):
        require_session("http://api.example.com")


def test_require_session_expires_exactly_at_exp(monkeypatch: pytest.MonkeyPatch) -> None:
    save_with(token=make_jwt(EXP_2100))
    monkeypatch.setattr(session_module, "_now", lambda: datetime(2100, 1, 1, tzinfo=UTC))
    with pytest.raises(SessionError, match="expired"):
        require_session("http://api.example.com")


def test_require_session_valid_just_before_exp(monkeypatch: pytest.MonkeyPatch) -> None:
    session = save_with(token=make_jwt(EXP_2100))
    monkeypatch.setattr(
        session_module, "_now", lambda: datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC)
    )
    assert require_session("http://api.example.com") == session


def test_require_session_unreadable_expiry_is_allowed() -> None:
    session = save_with(token="tok-123")
    assert require_session("http://api.example.com") == session
