# Contributing to geek42

Thanks for your interest! This document describes how to contribute code,
docs, or bug reports to geek42.

## Code of conduct

Be kind. Assume good faith. If you're unsure, ask.

## Development setup

geek42 uses [uv](https://docs.astral.sh/uv/) for environment management.

```sh
git clone https://github.com/OWNER/geek42.git
cd geek42
uv sync --frozen --dev

# Install pre-commit hooks (one-time, required)
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
uv run pre-commit install --hook-type pre-push
```

### Helper scripts

| Script | Command | Purpose |
|--------|---------|---------|
| Regenerate requirements | `uv run python scripts/regen_requirements.py` | Rewrites `requirements.txt` + `requirements-dev.txt` from `uv.lock` (hash-pinned, committed) |
| Supply-chain audit | `uv run python scripts/audit.py` | Runs the same checks as the CI `audit` job locally |

### Pre-commit hooks

Once installed, the hooks run automatically on `git commit` and
`git push`. They enforce:

- **On commit:**
  - `ruff check --fix` (security rules, style, auto-fix)
  - `ruff format`
  - `ty check` (type checking)
  - `uv lock` (sync lockfile with pyproject.toml)
  - `regen-requirements` (auto-regenerates `requirements*.txt` when
    `pyproject.toml` or `uv.lock` changes)
  - `gitleaks` (secret detection)
  - Whitespace, EOF, mixed line endings
  - YAML/TOML/JSON validity
  - No merge conflict markers
  - No large files (> 500 KB)
  - No private keys
  - No direct commits to `main`
  - No `breakpoint()`/`pdb` leftovers
- **On commit message:**
  - Conventional Commits format (`feat`, `fix`, etc.)
- **On push:**
  - Full `pytest` suite
  - `scripts/audit.py` — pip-audit (prod + dev) + CycloneDX SBOMs

Because the hooks use `uv run`, they are **byte-identical** to what
CI runs — if pre-commit passes locally, CI will pass.

### Running checks manually

```sh
# Run all hooks on all files
uv run pre-commit run --all-files

# Run a single hook
uv run pre-commit run ruff-check --all-files

# Skip hooks for a commit (emergency use only)
git commit --no-verify -S -s -m "chore: emergency fix"

# Individual tools
uv run pytest
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check
```

All of the above must pass locally before submitting a PR.

## Signed commits are required

All commits merged to `main` **must be cryptographically signed**. GitHub
will reject unsigned commits on protected branches.

Choose one of:

### GPG

```sh
gpg --full-generate-key
git config --global user.signingkey <KEYID>
git config --global commit.gpgsign true
# Upload the public key to GitHub: Settings → SSH and GPG keys
```

### SSH (recommended if you already use SSH keys)

```sh
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
# Add the key to GitHub as a "signing key"
```

### Sigstore / gitsign (keyless)

```sh
# Install gitsign: https://github.com/sigstore/gitsign
git config --global gpg.x509.program gitsign
git config --global gpg.format x509
git config --global commit.gpgsign true
# No key management needed — uses OIDC via your GitHub identity
```

## Developer Certificate of Origin (DCO)

By contributing, you certify that you wrote the code or have the right to
submit it under the project's CC0 license. Sign off every commit:

```sh
git commit -s -m "feat: add foo"
```

This appends a `Signed-off-by:` trailer per the
[DCO](https://developercertificate.org/).

## Commit message style — Conventional Commits (required)

**Every commit must follow [Conventional Commits](https://www.conventionalcommits.org/).**
This is enforced by CI; non-conforming commits block the merge.

### Format

```
<type>(<optional-scope>): <subject>

<optional body wrapped at 72 cols>

<optional footers>
```

Rules:

- Subject ≤ 72 characters, imperative mood, **no trailing period**
- Body wraps at 72 characters, blank line between subject and body
- One commit = one logical change (split unrelated work into separate commits)
- Always sign (`-S`) and sign-off (`-s`) — combine as `git commit -S -s`

### Allowed types

| Type | Use for | Triggers |
|------|---------|----------|
| `feat` | User-visible feature | minor version |
| `fix` | Bug fix | patch version |
| `security` | Security-relevant fix | patch/minor |
| `perf` | Performance improvement | patch |
| `docs` | Docs-only change | — |
| `test` | Tests only | — |
| `refactor` | Neither feature nor fix | — |
| `style` | Whitespace / formatting | — |
| `chore` | Tooling, deps, housekeeping | — |
| `ci` | CI/CD configuration | — |
| `build` | Build system / packaging | — |

### Scope (optional)

Use module names: `parser`, `linter`, `cli`, `compose`, `tracker`,
`site`, `feeds`, `renderer`, `ci`, `deps`, `docs`, `release`.

### Examples

```text
feat(cli): add read-new command

Reads all unread items sequentially and marks each as read, mirroring
`eselect news read new`.

Refs: #12
Signed-off-by: Jane Doe <jane@example.org>
```

```text
fix(parser): handle missing blank line between headers and body

Signed-off-by: Jane Doe <jane@example.org>
```

```text
security(site): resolve git executable via shutil.which

Pin to absolute path at import time to mitigate PATH hijacking.

Signed-off-by: Jane Doe <jane@example.org>
```

### Breaking changes

Append `!` after the type/scope **and** include a `BREAKING CHANGE:`
footer. This bumps the major version on release:

```text
feat(cli)!: rename `list` to `ls`

BREAKING CHANGE: `geek42 list` is now `geek42 ls`.

Signed-off-by: Jane Doe <jane@example.org>
```

For a complete reference and rationale see [docs/devops.md](docs/devops.md#semantic-commits-conventional-commits).

## Pull request checklist

- [ ] Tests added/updated for new behavior
- [ ] `uv run pytest` passes with ≥ 80% coverage
- [ ] `uv run ruff check` passes
- [ ] `uv run ruff format --check` passes
- [ ] `uv run ty check` passes
- [ ] `CHANGELOG.md` updated under `## Unreleased`
- [ ] Commits are signed and include DCO sign-off

## Reporting security issues

**Do not open public issues for security vulnerabilities.** See
[SECURITY.md](SECURITY.md) for private reporting channels.

## Reporting bugs

Open a GitHub issue with:

- What you were doing
- What you expected
- What happened instead
- Output of `uv run geek42 --version` and `python --version`
- Minimal reproduction if possible

## License

By contributing, you agree that your contributions will be released under
the same [CC0 1.0 Universal](LICENSE.md) license as the project itself.
