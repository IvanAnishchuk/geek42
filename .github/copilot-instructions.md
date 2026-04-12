# Copilot instructions for geek42

## Project

Pure Python CLI tool (Python 3.13+) using uv, hatchling, typer, rich,
pydantic. Converts GLEP 42 Gentoo news repos into static blogs.

## Conventions

- **Commits:** Conventional Commits format required (`feat:`, `fix:`, etc.)
- **Formatting:** ruff (line length 100, target py313)
- **Type checking:** ty
- **Testing:** pytest with 75% coverage floor
- **Package manager:** uv (never raw pip)
- **No shell scripts or Makefiles** — all tooling is Python

## Version locations

When bumping version, update ALL of:
- `pyproject.toml`
- `src/geek42/__init__.py`
- `Dockerfile`
- `packaging/debian/changelog`
- `packaging/rpm/geek42.spec`
- New ebuild in `packaging/gentoo/`

## Security

- All subprocess calls use list args (no shell=True)
- Exception catches should be as narrow as possible
- URLs must be validated before fetching
- Every noqa comment must document why it's necessary
- Supply-chain: SLSA L3, sigstore, PEP 740 attestations on every release

## Workflow

- Never push to main directly — always use PRs
- Signed commits and signed tags required
- Run `uv run pre-commit run --all-files` before pushing
- Merge commits only (no squash, no rebase)
- Owners may use `--admin` to bypass review requirement for their own PRs
- Never use `--admin` to bypass required CI checks

## Review process

When reviewing PRs:
- Triage every comment, including low-confidence hidden ones
- For actionable findings: fix in the PR or create a GitHub issue and link it
- Never dismiss comments without explicit owner confirmation
- Reply with linked issue number or reason before resolving conversations
- After changes are made, re-review before approving
