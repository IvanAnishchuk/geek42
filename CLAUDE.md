# CLAUDE.md

## Project Overview

geek42 — Convert GLEP 42 Gentoo news repositories into static blogs.

CLI tool built with typer + rich. Source layout under `src/geek42/`.
Released to PyPI with SLSA L3 provenance, sigstore signing, and
PEP 740 attestations.

## Commands

```bash
# Install dependencies
uv sync --frozen --dev

# Run the CLI
uv run geek42 --help

# Run tests with coverage
uv run pytest

# Lint + format
uv run ruff check --fix src/ tests/ scripts/
uv run ruff format src/ tests/ scripts/

# Type check
uv run ty check

# Full pre-commit suite (run before every push)
uv run pre-commit run --all-files

# Supply-chain audit (pip-audit + SBOM)
uv run python scripts/audit.py

# Download and verify a release
uv run python scripts/download_release.py 0.4.2a7
uv run python scripts/verify_provenance.py 0.4.2a7
uv run python scripts/verify_cosign.py 0.4.2a7
uv run python scripts/verify_pure.py 0.4.2a7
```

## Conventions

- Python 3.13+, src layout, hatchling build backend
- Ruff for linting (line-length 100, security rules enabled) and formatting
- ty for type checking
- pytest with coverage (75% floor)
- Conventional Commits enforced by pre-commit hook
- All CI checks must pass before merge (see .github/workflows/ci.yml)
- No checked-in shell scripts or Makefiles — prefer Python scripts for tooling

## Critical workflow rules

- **Never push directly to main.** Always create a PR branch and merge.
- **Never delete tags or force-push.** Versions and releases are immutable.
- **All commits must be signed.** Configure GPG, SSH, or gitsign (see CONTRIBUTING.md).
- **Always use signed tags:** `git tag -s`, never `-a` or lightweight.
- **Always use merge commits** when merging PRs (no squash, no rebase).
- **Always run pre-commit before pushing.**
- **Never amend published commits.** Create new commits to fix issues.
- **`--admin` merge:** Owners may use `--admin` to bypass the review
  requirement when committing and merging their own work. Never use
  `--admin` to bypass required CI checks — all status checks must pass.

## Version management

Version must be updated in ALL of these files simultaneously:
- `pyproject.toml` (`version = "..."`)
- `src/geek42/__init__.py` (`__version__ = "..."`)
- `Dockerfile` (`ARG VERSION=...`)
- `packaging/debian/changelog` (new entry)
- `packaging/rpm/geek42.spec` (`Version:` + `%changelog`)
- `packaging/gentoo/app-text/geek42/geek42-{ver}.ebuild` (new file)

After updating `pyproject.toml`, always run:
```bash
uv lock
uv run python scripts/regen_requirements.py
```

### PEP 440 version format

- Alpha: `0.4.2a7`
- Beta: `0.4.2b1`
- Release candidate: `0.4.2c1` (PEP 440 alias for `rc`)
- Dev: `0.4.2a3.dev1`
- Gentoo: `0.4.2_alpha7`, `0.4.2_beta1`, `0.4.2_rc1`

## Branch naming

- Release: `release/0.4.2a7` (match PEP 440 exactly, no hyphens)
- Feature: `feat/description`
- Fix: `fix/description`
- Chore: `chore/description`

## Release process

1. Create `release/{version}` branch from main
2. Bump version in ALL files listed above
3. Update `CHANGELOG.md`
4. Run `uv lock` + `uv run python scripts/regen_requirements.py`
5. Commit, push, create PR
6. Wait for CI, address review comments, merge (`--admin` OK for owner's own PRs)
7. Create signed tag: `git tag -s v{version} -m "Release v{version}"`
8. Push tag: `git push origin v{version}`

The release workflow handles: build, attest, sign, publish, create GitHub Release.
Pre-release tags (containing `a`, `b`, `c`, `dev`) route to TestPyPI.

## Supply-chain security

Every release produces:
- `geek42-{ver}-SHA256SUMS.txt` — checksums
- `*.sigstore.json` — sigstore bundles
- GitHub attestations via `actions/attest`
- `geek42-v{ver}-provenance.intoto.jsonl` — SLSA L3 provenance
- PEP 740 attestations — automatic via trusted publishing

Three verification scripts with full parity (all require `gh` for
downloading proofs via `download_release.py`):
- `verify_provenance.py` — gh + sigstore CLI + slsa-verifier + pypi-attestations
- `verify_cosign.py` — cosign + gh (for proof download)
- `verify_pure.py` — sigstore + pypi-attestations Python libs + gh (for proof download)

Proof files: `proofs/{github,pypi}/`. Distribution files: `dist/`.

## Pull request review process

After creating a PR:

1. **Request AI reviews** on every PR (Copilot, Gemini Code Assist, etc.).
2. **Triage every review comment**, including low-confidence hidden ones.
   Expand "Show hidden" to see all comments — don't skip them.
3. **For each actionable comment:**
   - Fix it in the PR if small, OR
   - Create a GitHub issue for it and link the issue in a reply before
     resolving the conversation.
4. **Never dismiss review comments** without explicit owner confirmation.
   Reply with the reason or linked issue before resolving.
5. **For non-actionable comments:** reply with why it's not applicable,
   get owner confirmation, then resolve.
6. **After addressing comments**, request a new review and wait for it
   to complete before merging. Repeat until all comments are resolved.

This applies to all reviewers: Copilot, Gemini Code Assist, Codex, and humans.

## Code quality

- All `# noqa` comments must document why the suppression is necessary
- Prefer narrow exception types over broad `Exception` catches
- Validate external inputs (URLs, version strings) before use
- `uv.lock` and `requirements*.txt` are always committed
- Run `uv run pre-commit run --all-files` before pushing
- After `sed` or other non-interactive bulk edits, always review
  `git diff` before committing to verify no unintended changes
