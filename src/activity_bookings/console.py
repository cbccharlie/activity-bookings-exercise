"""Shared Rich consoles: all user-facing output goes through these."""

from rich.console import Console

console = Console()
err_console = Console(stderr=True)
