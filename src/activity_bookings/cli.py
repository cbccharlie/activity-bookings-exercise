"""Root Typer application and console entry point."""

from pathlib import Path
from typing import Annotated

import typer

from activity_bookings import __version__
from activity_bookings.commands import config_cmd
from activity_bookings.console import console

app = typer.Typer(
    name="activity-bookings",
    help="ActivityBookings command line client.",
    no_args_is_help=True,
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
    """ActivityBookings command line client."""
    ctx.obj = config


app.command("config")(config_cmd.config)


def main() -> None:
    """Console script entry point."""
    app(prog_name="activity-bookings")
