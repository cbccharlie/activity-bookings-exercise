"""Local session storage: the JWT returned by the API and the logged-in user."""

import base64
import binascii
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from activity_bookings.api_client import User, parse_user
from activity_bookings.config import config_dir
from activity_bookings.errors import ApiResponseError, SessionError

LOGIN_HINT = "run 'activity-bookings auth login' to start a new session"


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


def load_session(path: Path | None = None) -> Session | None:
    """Read the saved session, or return None if there is none.

    An unreadable or malformed file raises SessionError with its path and a login hint.
    """
    target = path if path is not None else default_session_path()
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _invalid_session(target, exc.strerror or str(exc)) from exc

    try:
        data = json.loads(text)
    except ValueError as exc:
        raise _invalid_session(target, "not valid JSON") from exc
    return _from_json(data, target)


def delete_session(path: Path | None = None) -> bool:
    """Delete the session file without reading it. Return False if there was none."""
    target = path if path is not None else default_session_path()
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    except OSError as exc:
        cause = exc.strerror or str(exc)
        raise SessionError(f"the session file {target} could not be removed: {cause}") from exc
    return True


def token_expiry(token: str) -> datetime | None:
    """Return the `exp` claim of a JWT as a UTC datetime, without verifying it.

    Returns None if the token is not a JWT or has no readable integer `exp`.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, binascii.Error):
        return None
    exp = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(exp, bool) or not isinstance(exp, int):
        return None
    try:
        return datetime.fromtimestamp(exp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def require_session(api_url: str) -> Session:
    """Return the saved session for `api_url`, for commands that call protected routes.

    Raises SessionError, without any HTTP request, if there is no session, the file is invalid,
    it belongs to another API or its token has expired according to its `exp` claim. A token
    whose expiry cannot be read is accepted: the server decides.
    """
    session = load_session()
    if session is None:
        raise SessionError(
            "not logged in; run 'activity-bookings auth login' or 'activity-bookings auth register'"
        )
    if session.api_url.rstrip("/") != api_url.rstrip("/"):
        raise SessionError(
            f"the session belongs to {session.api_url}, but the configured API is {api_url}; "
            "run 'activity-bookings auth login'"
        )
    expiry = token_expiry(session.access_token)
    if expiry is not None and expiry <= _now():
        raise SessionError(
            f"your session expired on {expiry.strftime('%Y-%m-%d %H:%M')} UTC; "
            "run 'activity-bookings auth login'"
        )
    return session


def _now() -> datetime:
    return datetime.now(UTC)


def _from_json(data: object, target: Path) -> Session:
    if not isinstance(data, dict):
        raise _invalid_session(target, "not a JSON object")
    for key in ("api_url", "access_token"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise _invalid_session(target, f"missing or invalid '{key}'")
    try:
        user = parse_user(data.get("user"))
    except ApiResponseError as exc:
        raise _invalid_session(target, "missing or invalid 'user'") from exc
    return Session(api_url=data["api_url"], access_token=data["access_token"], user=user)


def _invalid_session(target: Path, cause: str) -> SessionError:
    return SessionError(f"invalid session file {target}: {cause}; {LOGIN_HINT}")
