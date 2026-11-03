# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project overview

ActivityBookings CLI (`activity-bookings` command, `activity_bookings` package) is a Python console
client for the ActivityBookings REST API, an activity booking system used for training sessions and
demos (not for production). It covers account (register/login with JWT), browsing activities,
bookings and managing your own activities. There is no local database.

- API contract: `docs/api-reference.md`. Read it before proposing anything that calls the API, and
  follow the real server behaviour, not its README.
- Product context and per-artifact rules: `openspec/config.yaml`.

## Tech stack

- Python 3.12+, managed with uv and `pyproject.toml` (`src/` layout, `uv_build` backend).
- Typer for the CLI, Rich for console output, httpx for HTTP (JWT auth on protected routes).
- `tomllib` (stdlib) for the user config file (`~/.config/activity-bookings/config.toml`).
- pytest + respx for tests, ruff for lint and format, mypy in strict mode.

## Commands

```bash
uv sync                              # install/update the environment from uv.lock
uv run activity-bookings --help      # run the CLI
uv run pytest                        # tests
uv run ruff check                    # lint
uv run ruff format                   # format (use --check to verify only)
uv run mypy src tests                # type check (strict)
```

Before finishing any task, run the full check and make sure everything passes:

```bash
uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest
```

## Project layout

```
src/activity_bookings/
  __init__.py      # __version__ via importlib.metadata
  __main__.py      # python -m activity_bookings
  cli.py           # root Typer app: global options (--version, --config), subcommand registry, main()
  config.py        # Settings, load_settings(), config_dir(), default_config_path()
  errors.py        # ActivityBookingsError (base), ConfigError, ApiError, ApiConnectionError,
                   # ApiResponseError, SessionError, handle_errors
  console.py       # Rich consoles: console (stdout) and err_console (stderr)
  api_client.py    # ApiClient (httpx, optional Bearer token), models (User, AuthResult, Activity,
                   # NewActivity, ActivityChanges), error translation
  session.py       # Session, save/load/delete_session() (session.json, mode 0600), token_expiry(),
                   # require_session() for protected routes
  commands/        # one module per command group
    _auth.py       # protected-route helpers: authorized_client(), login_hint() (401 → login hint)
    config_cmd.py  # `config`
    auth_cmd.py    # `auth` group: `register`, `login`, `logout`, `whoami`
    activities_cmd.py  # `activities` group: `list`, `create`, `update`, `delete`
tests/
  conftest.py      # CliRunner fixture, isolated HOME / XDG_CONFIG_HOME
  test_cli.py
  test_config.py
  test_api_client.py
  test_session.py
  test_auth_cmd.py
  test_activities_cmd.py
  test_auth_helpers.py
  jwt_helpers.py   # make_jwt() to build unsigned JWTs in tests
```

New command groups go in a new module under `commands/` and are registered in `cli.py`.

## Code conventions

- Type hints everywhere; code must pass `mypy --strict`. Line length 100.
- Small functions. Typed data models as dataclasses (frozen where possible).
- HTTP only in the API client layer; commands stay thin and delegate to it.
- Domain errors subclass `ActivityBookingsError`. Commands use `handle_errors`, which prints
  `Error: <message>` to stderr and exits with code 1. Translate API errors into clear messages;
  never show a traceback for expected failures.
- Print only through the Rich consoles in `console.py`; no bare `print()`.
- Code, identifiers, docstrings and CLI text in English.
- Commit messages in Spanish, Conventional Commits, always on `develop`: use the `commit` skill.

## Testing

- pytest with `typer.testing.CliRunner` for CLI behaviour; call functions directly for unit tests.
- Always mock HTTP with respx. Tests must never hit a real API.
- Keep the autouse fixture that isolates `HOME` and `XDG_CONFIG_HOME` in `tmp_path`.
- One test (at least) per spec scenario; assert on substrings of output and on exit codes.

## OpenSpec workflow

Behaviour changes go through an OpenSpec change. Current specs live in `openspec/specs/`, active
changes in `openspec/changes/`.

1. If the change calls the API, use the `api-explorer` subagent first (and refresh
   `docs/api-reference.md` if it is outdated).
2. `/opsx:propose` to create proposal, specs, design and tasks (`/opsx:explore` to think first,
   `/opsx:update` to revise them).
3. `/opsx:apply` to implement. Mark a task `[x]` only when its tests pass.
4. Use the `spec-reviewer` subagent to review the change against its specs and this file.
5. `/opsx:archive` once the full check passes.

OpenSpec artifacts (proposal, design, specs, tasks) are written in Spanish; code stays in English.
If a change alters the stack, commands or layout, update this file in the same change.

## Boundaries

Do not, unless the user explicitly asks:

- Add dependencies without justifying them in the change's `design.md`.
- Use pip, poetry or any tool other than uv; never edit `uv.lock` by hand.
- Commit, push or create branches (invoking the `commit` skill counts as asking to commit).
- Call the real API from tests, or write code outside an OpenSpec change for behaviour changes.
- Disable ruff rules, mypy checks or tests to make the check pass.
