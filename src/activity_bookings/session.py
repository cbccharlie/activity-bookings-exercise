"""Local session storage: the JWT returned by the API and the logged-in user."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from activity_bookings.api_client import User
from activity_bookings.config import config_dir
from activity_bookings.errors import SessionError


@dataclass(frozen=True)
class Session:
    """A logged-in session against a given API."""

    api_url: str
    access_token: str
    user: User


def default_session_path() -> Path:
    """Return `session.json` inside the configuration directory."""
    return config_dir() / "session.json"


def save_session(session: Session, path: Path | None = None) -> Path:
    """Write the session as JSON with mode 0600, atomically replacing any previous one.

    Returns the path written; any filesystem failure raises SessionError.
    """
    target = path if path is not None else default_session_path()
    content = json.dumps(_to_json(session), indent=2) + "\n"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_atomically(target, content)
    except OSError as exc:
        cause = exc.strerror or str(exc)
        raise SessionError(f"the session could not be saved to {target}: {cause}") from exc
    return target


def _to_json(session: Session) -> dict[str, object]:
    user = session.user
    return {
        "api_url": session.api_url,
        "access_token": session.access_token,
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


def _write_atomically(target: Path, content: str) -> None:
    """Write to a 0600 temporary file in the same directory, then rename it over `target`."""
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
