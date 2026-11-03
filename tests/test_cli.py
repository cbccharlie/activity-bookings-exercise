import subprocess
import sys

import typer
from typer.testing import CliRunner

from activity_bookings import __version__
from activity_bookings.cli import app
from activity_bookings.errors import ActivityBookingsError, handle_errors


def test_help_shows_program_and_subcommands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "activity-bookings" in result.stdout
    assert "config" in result.stdout


def test_module_execution_shows_same_help(runner: CliRunner) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "activity_bookings", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Usage: activity-bookings" in proc.stdout
    assert "config" in proc.stdout
    assert "--version" in proc.stdout


def test_no_arguments_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, [])
    assert "Usage:" in result.output
    assert "config" in result.output
    assert "API URL" not in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"activity-bookings {__version__}" in result.stdout


def test_unknown_subcommand_is_usage_error(runner: CliRunner) -> None:
    result = runner.invoke(app, ["foo"])
    assert result.exit_code == 2
    assert "No such command" in result.stderr


def test_unknown_option_is_usage_error(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--foo"])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


def test_application_error_is_readable(runner: CliRunner) -> None:
    probe = typer.Typer()

    @probe.command()
    @handle_errors
    def fail() -> None:
        raise ActivityBookingsError("something went wrong")

    result = runner.invoke(probe, [])
    assert result.exit_code == 1
    assert "Error: something went wrong" in result.stderr
    assert "Traceback" not in result.output
