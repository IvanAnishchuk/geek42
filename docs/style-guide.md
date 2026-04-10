# Style Guide and Conventions

Coding and project conventions for geek42. Automated where possible,
documented here for the rest.

---

## Commits

**Conventional Commits** (enforced by `conventional-pre-commit` hook):

```
type(scope): description

[optional body]

[optional footer(s)]
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`,
`perf`, `security`, `ci`, `build`, `revert`.

Scopes are freeform but common ones: `news`, `cli`, `ci`, `deps`,
`deps-dev`.

Examples:
- `feat(news): add 2026-04-10-my-topic`
- `fix(cli): handle missing config gracefully`
- `chore(deps): bump pydantic to 2.11`
- `docs: update quickstart`

Dependabot uses `chore(deps)`, `chore(deps-dev)`, `chore(ci)`.

## Versioning

**Semantic Versioning** (SemVer):

- `feat` commits bump **minor** (0.3.0 -> 0.4.0)
- `fix` commits bump **patch** (0.3.0 -> 0.3.1)
- Breaking changes (rare) bump **major** (0.x -> 1.0)

Version is declared in `pyproject.toml` and `src/geek42/__init__.py`.
Both must match. Packaging metadata (debian, rpm, ebuild) tracks the
same version.

## Python style

**Tooling**: ruff handles all formatting and linting. No manual style
decisions needed — run `ruff format` and `ruff check --fix`.

Key settings (`pyproject.toml`):
- Line length: **100**
- Target: **Python 3.13**
- Rules: E, F, W, I, UP, B, SIM, S, BLE, TRY

Conventions not enforced by ruff:
- Use `from __future__ import annotations` in every module.
- Prefer `Path` over string paths.
- Use `Field(description=...)` on all Pydantic model fields.
- Lazy imports for heavy modules (`from .blog import compile_news`
  inside functions, not at module top).
- Subprocess calls: resolve executables via `shutil.which()` to
  absolute paths (S607 compliance). Annotate with `# noqa: S603`
  when args are controlled.

## News item style (GLEP 42)

- Wrap body lines at **72 characters** (W002 warning in our linter).
- Title max **50 characters** (W001 warning).
- Author format: `Name <email>` (W004 warning).
- Use `News-Item-Format: 2.0` for new items.
- Filenames: `YYYY-MM-DD-slug.en.txt` where slug is lowercase
  alphanumeric + hyphens, max 20 chars.

## File organization

```
src/geek42/
  __init__.py    Public API re-exports + __version__
  cli.py         Typer commands (thin, delegates to other modules)
  models.py      Pydantic models (NewsItem, NewsSource, SiteConfig)
  parser.py      GLEP 42 file parser + repo scanner
  compose.py     Editor integration, template generation, placement
  site.py        Static site builder (pull, collect, build)
  blog.py        Markdown compilation + README index
  manifest.py    Gemato Manifest generation + verification
  scaffold.py    Newsrepo template (init command)
  linter.py      News file diagnostics
  feeds.py       RSS + Atom generation
  renderer.py    HTML + Markdown rendering
  tracker.py     Read/unread state
  errors.py      Exception hierarchy
  templates/     Jinja2 HTML templates
```

## Pre-commit hooks

All hooks are declared in `.pre-commit-config.yaml`. Contributors
install with:

```sh
uv sync --dev
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

The hooks enforce:
- Trailing whitespace removal
- LF line endings
- YAML/TOML validity
- Merge conflict markers
- ruff format + check
- ty type check
- uv lock sync
- Conventional commit messages
- No direct commits to main

## CI / local parity

The CI `pre-commit` job runs the same hooks as local development
(minus `no-commit-to-branch` and `gemato-sign` which are
local-only). If pre-commit passes locally, it passes in CI.

## Documentation

- `README.md`: user-facing quickstart and reference
- `CHANGELOG.md`: Keep a Changelog format, under `[Unreleased]`
  during development
- `docs/`: detailed guides (not auto-generated)
- Docstrings: public API functions get docstrings; internal helpers
  get them only when the logic isn't obvious
- No auto-generated API docs for now — the codebase is small enough
  that `__init__.py` + docstrings suffice
