from pathlib import Path

import pytest
from typer.testing import CliRunner

from activity_bookings.cli import app
from activity_bookings.config import (
    DEFAULT_API_URL,
    Settings,
    default_config_path,
    load_settings,
)
from activity_bookings.errors import ConfigError


def write_config(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --- default_config_path -------------------------------------------------------------


def test_default_path_without_xdg(isolated_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert default_config_path() == isolated_env / ".config" / "activity-bookings" / "config.toml"


def test_default_path_with_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    assert default_config_path() == tmp_path / "cfg" / "activity-bookings" / "config.toml"


# --- load_settings -------------------------------------------------------------------


def test_load_valid_file() -> None:
    path = write_config(default_config_path(), 'api_url = "http://api.example.com"\n')
    assert load_settings() == Settings(api_url="http://api.example.com", source=path)


def test_load_missing_default_file_uses_default() -> None:
    assert load_settings() == Settings(api_url=DEFAULT_API_URL, source=None)


def test_load_file_without_api_url_uses_default() -> None:
    write_config(default_config_path(), "other = 1\n")
    assert load_settings().api_url == DEFAULT_API_URL


def test_load_ignores_unknown_keys() -> None:
    write_config(default_config_path(), 'api_url = "http://api.example.com"\nfoo = 1\n')
    assert load_settings().api_url == "http://api.example.com"


def test_load_strips_trailing_slash() -> None:
    write_config(default_config_path(), 'api_url = "http://api.example.com/"\n')
    assert load_settings().api_url == "http://api.example.com"


def test_load_explicit_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "no-existe.toml"
    with pytest.raises(ConfigError, match="not found") as exc:
        load_settings(missing)
    assert str(missing) in str(exc.value)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("api_url = \n", "invalid TOML"),
        ('api_url = "ftp://example.com"\n', "http(s) URL"),
        ('api_url = "http://"\n', "http(s) URL"),
        ('api_url = "localhost:3000"\n', "http(s) URL"),
        ("api_url = 3000\n", "must be a string"),
    ],
)
def test_load_invalid_file(content: str, expected: str) -> None:
    path = write_config(default_config_path(), content)
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert expected in str(exc.value)
    assert str(path) in str(exc.value)


# --- `config` command ----------------------------------------------------------------


def test_config_default_location(
    runner: CliRunner, isolated_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME")
    path = write_config(
        isolated_env / ".config" / "activity-bookings" / "config.toml",
        'api_url = "http://api.example.com"\n',
    )
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "http://api.example.com" in result.stdout
    assert str(path) in result.stdout


def test_config_xdg_location(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    write_config(
        tmp_path / "cfg" / "activity-bookings" / "config.toml",
        'api_url = "http://xdg.example.com"\n',
    )
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "http://xdg.example.com" in result.stdout


def test_config_explicit_path(runner: CliRunner, tmp_path: Path) -> None:
    path = write_config(tmp_path / "custom.toml", 'api_url = "http://custom.example.com"\n')
    result = runner.invoke(app, ["--config", str(path), "config"])
    assert result.exit_code == 0
    assert "http://custom.example.com" in result.stdout
    assert str(path) in result.stdout


def test_config_default_value(runner: CliRunner) -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert DEFAULT_API_URL in result.stdout
    assert "default" in result.stdout


def test_config_file_without_api_url(runner: CliRunner) -> None:
    write_config(default_config_path(), "other = 1\n")
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert DEFAULT_API_URL in result.stdout


def test_config_unknown_keys(runner: CliRunner) -> None:
    write_config(default_config_path(), 'api_url = "http://api.example.com"\nfoo = 1\n')
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "http://api.example.com" in result.stdout


def test_config_trailing_slash(runner: CliRunner) -> None:
    write_config(default_config_path(), 'api_url = "http://api.example.com/"\n')
    result = runner.invoke(app, ["config"])
    assert "http://api.example.com " in result.stdout
    assert "http://api.example.com/" not in result.stdout


def test_config_explicit_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "no-existe.toml"
    result = runner.invoke(app, ["--config", str(missing), "config"])
    assert result.exit_code == 1
    assert "Error:" in result.stderr
    assert "not found" in result.stderr
    assert str(missing) in result.stderr


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("api_url = \n", "invalid TOML"),
        ('api_url = "ftp://example.com"\n', "must be an http(s) URL"),
        ("api_url = 3000\n", "must be a string"),
    ],
)
def test_config_invalid_file(runner: CliRunner, content: str, expected: str) -> None:
    path = write_config(default_config_path(), content)
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 1
    assert result.stderr.startswith("Error:")
    assert expected in result.stderr
    assert str(path) in result.stderr
    assert "Traceback" not in result.output


@pytest.mark.parametrize("args", [["--help"], ["--version"]])
def test_help_and_version_ignore_invalid_config(runner: CliRunner, args: list[str]) -> None:
    write_config(default_config_path(), "api_url = \n")
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "Error" not in result.output
