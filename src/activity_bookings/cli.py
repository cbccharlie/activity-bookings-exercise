"""Root Typer application and console entry point."""

import contextlib
import sys
from pathlib import Path
from typing import Annotated

import typer
import typer.main

from activity_bookings import __version__, interactive
from activity_bookings.commands import activities_cmd, auth_cmd, bookings_cmd, config_cmd
from activity_bookings.console import console

app = typer.Typer(
    name="activity-bookings",
    help="ActivityBookings command line client.",
    invoke_without_command=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"activity-bookings {__version__}", highlight=False)
        raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to the configuration file.", dir_okay=False),
    ] = None,
) -> None:
    """ActivityBookings command line client.

    Run it without a command in a terminal to choose actions from an interactive menu.
    """
    ctx.obj = config
    if ctx.invoked_subcommand is not None:
        return
    if _is_interactive():
        interactive.run_menu(_make_prompter(), _executor(config))
        return
    typer.echo(ctx.get_help(), nl=False)  # Typer's rich help prints itself and returns ""
    raise typer.Exit(code=2)


def _is_interactive() -> bool:
    """True when both standard input and output are a terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _make_prompter() -> interactive.Prompter:
    return interactive.QuestionaryPrompter()


def _executor(config: Path | None) -> interactive.Execute:
    """Run a subcommand of this CLI from the menu, with the same `--config`, and return."""
    prefix = [] if config is None else ["--config", str(config)]

    def execute(args: list[str]) -> None:
        # Every subcommand ends with SystemExit, also on errors: return to the menu instead.
        with contextlib.suppress(SystemExit):
            typer.main.get_command(app).main([*prefix, *args], prog_name="activity-bookings")

    return execute


app.command("config")(config_cmd.config)
app.add_typer(auth_cmd.app, name="auth")
app.add_typer(activities_cmd.app, name="activities")
app.add_typer(bookings_cmd.app, name="bookings")


def main() -> None:
    """Console script entry point."""
    app(prog_name="activity-bookings")
