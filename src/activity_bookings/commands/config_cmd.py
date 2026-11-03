"""`config` subcommand: show the effective client configuration."""

from pathlib import Path

import typer
from rich.table import Table

from activity_bookings.config import default_config_path, load_settings
from activity_bookings.console import console
from activity_bookings.errors import handle_errors


@handle_errors
def config(ctx: typer.Context) -> None:
    """Show the effective configuration."""
    config_path: Path | None = ctx.obj
    settings = load_settings(config_path)

    if settings.source is not None:
        source = str(settings.source)
    else:
        default_path = default_config_path()
        if default_path.is_file():
            source = f"default (api_url not set in {default_path})"
        else:
            source = f"default (no config file found at {default_path})"

    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(overflow="fold")
    table.add_row("API URL", settings.api_url)
    table.add_row("Source", source)
    console.print(table)
