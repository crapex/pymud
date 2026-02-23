# AGENTS.md
# Guidance for agentic coding tools working in this repo.

## Repository overview
- Project: PyMUD, a Python MUD client.
- Python: >=3.8 (see `pyproject.toml`).
- Code lives in `src/pymud/`.
- Docs live in `docs/` (Sphinx).

## Build, lint, and test commands
These are the supported commands in this repo. Prefer running them from the repo
root unless noted.

### Build (package)
- Build sdist/wheel:
  - `python -m build`
- Validate built dist:
  - `python -m twine check dist/*`

### Lint
- Lint all Python files:
  - `flake8 .`

### Tests
- Run all tests (if present):
  - `python -m pytest`
- Run a single test module:
  - `python -m pytest tests/test_file.py`
- Run a single test by node id:
  - `python -m pytest tests/test_file.py::TestClass::test_name`
- Run tests matching a pattern:
  - `python -m pytest -k "pattern" tests`

### Tox (meta runner)
- Run the default tox envs:
  - `tox`
- Run a specific Python env:
  - `tox -e py38`
- Pass through pytest args:
  - `tox -e py38 -- -k "pattern"`

### Docs (Sphinx)
- Build docs (from repo root):
  - `make -C docs html`
- Equivalent explicit command:
  - `python -m sphinx -b html docs/source docs/build/html`

### Notes about tests
- The repo does not currently include a `tests/` directory. Tox is configured
  to run `py.test tests {posargs}`; if no tests exist, this will be a no-op.

## Code style and conventions
Follow existing patterns in `src/pymud/`.

### Formatting
- Indentation: 4 spaces.
- Max line length is not explicitly configured; keep lines reasonable.
- Use spaces around operators and after commas.

### Imports
- Order imports in three groups:
  1) Standard library
  2) Third-party
  3) Local package imports (`from .foo import Bar`)
- Keep imports explicit; avoid wildcard imports.
- Prefer `from collections.abc import Iterable` over `typing.Iterable`.

### Naming
- Classes: `CamelCase` (e.g., `SessionBuffer`).
- Functions and methods: `snake_case` (e.g., `exec_command`).
- Constants: `UPPER_SNAKE_CASE` when truly constant.
- Private/internal: prefix with `_` (e.g., `_tasks`).

### Types
- Type hints are used throughout; continue to annotate new public methods.
- Prefer `typing` and `collections.abc` types over concrete containers in
  public APIs (e.g., `Iterable`, `Optional`, `Union`, `Dict`, `List`, `Tuple`).
- Keep annotations compatible with Python >=3.8.

### Error handling and logging
- Favor explicit exceptions with helpful messages.
- Use existing logging patterns (`self.syslog`, `self.log`, or module loggers).
- For user-facing text, prefer `Settings.gettext(...)` to keep i18n coverage.
- Avoid swallowing exceptions silently; log or re-raise as appropriate.

### Async and concurrency
- The codebase is asyncio-driven; prefer async/await for IO paths.
- If adding tasks, use existing helpers (e.g., session task registries) to
  ensure cleanup and cancellation behavior is consistent.

### Data structures
- `DotDict` and related helpers are used in session state; follow existing
  patterns when extending session structures.
- Keep session state initialization in `Session.initialize()`.

### Public API stability
- This is a user-facing tool; minimize breaking changes to public APIs and
  configuration formats (`pymud.cfg`, session commands).
- New settings should be wired through `Settings` and documented.

## Project-specific conventions
- Use `Settings.client[...]` and `Settings.server[...]` for defaults.
- Use `Settings.gettext(key, *args)` for translatable strings.
- System commands live in `Session._sys_commands` and handler methods follow
  the `handle_<command>` naming pattern.
- Prefer `Path` from `pathlib` for filesystem work when feasible.

## Development workflows
- For packaging sanity checks, run: `python -m build` and
  `python -m twine check dist/*`.
- For linting, run: `flake8 .`.
- For tests, run pytest as above; if adding tests, keep them under `tests/`.
- For docs, use `make -C docs html`.

## Agent behavior expectations
- Do not introduce non-ASCII text unless the file already uses it or it is
  required for user-facing messages (the project includes Chinese i18n).
- Avoid sweeping refactors; make small, targeted changes unless requested.
- Preserve existing behavior and config semantics unless explicitly changing.

## Cursor / Copilot rules
- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md`
  were found in this repository at the time of writing.
