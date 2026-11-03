"""Client configuration: location, defaults and validation of the user TOML file."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from activity_bookings.errors import ConfigError

DEFAULT_API_URL = "http://localhost:3000"


@dataclass(frozen=True)
class Settings:
    """Effective client settings. `source` is None when the default API URL is used."""

    api_url: str
    source: Path | None


def default_config_path() -> Path:
    """Return `$XDG_CONFIG_HOME/activity-bookings/config.toml` (default `~/.config`)."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "activity-bookings" / "config.toml"


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from `path`, or from the default location if `path` is None.

    A missing default file falls back to the default API URL; a missing explicit
    file, invalid TOML or an invalid `api_url` raise ConfigError.
    """
    config_path = path if path is not None else default_config_path()
    if not config_path.is_file():
        if path is not None:
            raise ConfigError(f"configuration file not found: {config_path}")
        return Settings(api_url=DEFAULT_API_URL, source=None)

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    if "api_url" not in data:
        return Settings(api_url=DEFAULT_API_URL, source=None)
    return Settings(api_url=_validate_api_url(data["api_url"], config_path), source=config_path)


def _validate_api_url(value: object, config_path: Path) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"invalid api_url in {config_path}: must be a string")
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ConfigError(
            f"invalid api_url {value!r} in {config_path}: must be an http(s) URL with a host"
        )
    return value.rstrip("/")
