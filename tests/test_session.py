import json
import stat
import sys
from pathlib import Path

import pytest

from activity_bookings.api_client import User
from activity_bookings.errors import SessionError
from activity_bookings.session import Session, default_session_path, save_session

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
