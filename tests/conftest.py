from pathlib import Path

import pytest
from typer.testing import CliRunner

from activity_bookings.console import console, err_console


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never read the developer's real configuration; keep Rich output on one line."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(console, "width", 500)
    monkeypatch.setattr(err_console, "width", 500)
    return home
