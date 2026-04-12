# DevOps & CI/CD Reference

This document describes **how geek42 is built, tested, and shipped**.
For security architecture see [security.md](security.md); for repo
owner setup see [security-setup.md](security-setup.md).

## Tooling overview

| Tool | Purpose | Config |
|------|---------|--------|
| [uv](https://docs.astral.sh/uv/) | Environment, resolver, lock, build frontend | `pyproject.toml`, `uv.lock` |
| [hatchling](https://hatch.pypa.io/latest/config/build/) | Build backend (PEP 517) | `[tool.hatch.*]` in `pyproject.toml` |
| [ruff](https://docs.astral.sh/ruff/) | Linter, formatter, import sort, security scan | `[tool.ruff.*]` |
| [ty](https://github.com/astral-sh/ty) | Fast static type checker | `[tool.ty.*]` |
| [pytest](https://docs.pytest.org/) | Test runner | `[tool.pytest.*]` |
| [coverage.py](https://coverage.readthedocs.io/) | Branch + line coverage | `[tool.coverage.*]` |
| [pip-audit](https://pypi.org/project/pip-audit/) | CVE scan of installed deps | — |
| [cyclonedx-bom](https://cyclonedx.github.io/cyclonedx-python/) | SBOM generation | — |
| [pre-commit](https://pre-commit.com/) | Git hook orchestrator | `.pre-commit-config.yaml` |

Everything runs through `uv run` — no virtualenv activation needed.

### Why `uv run` everywhere?

The `.pre-commit-config.yaml` uses `language: system` with `uv run
<tool>` as the entry point for ruff, ty, pytest, and pip-audit. This
guarantees that the local hooks invoke the **exact same binaries**
managed by `uv.lock` that CI uses. There is zero drift between
"works on my machine" and CI outcomes.

---

## Local development loop

### One-time setup

```sh
git clone https://github.com/IvanAnishchuk/geek42.git
cd geek42
uv sync --frozen --dev

# Install git hooks (required)
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
uv run pre-commit install --hook-type pre-push
```

This creates `.venv/`, resolves all dependencies (production + dev)
from `uv.lock` with hash verification, installs geek42 in editable
mode, and wires up git hooks.

### Helper scripts

geek42 ships two Python helper scripts under `scripts/` for tasks
that need to stay consistent with CI. They depend only on the project
environment (`uv`, `rich`, `pip-audit`, `cyclonedx-bom`) — no bash,
no Make, no extra task runner.

| Script | Command | What it does |
|--------|---------|--------------|
| Regenerate requirements | `uv run python scripts/regen_requirements.py` | Runs `uv lock`, exports `requirements.txt` (prod) and `requirements-dev.txt` (prod + dev). Both are hash-pinned and **committed to the repo**. |
| Supply-chain audit | `uv run python scripts/audit.py` | Runs the full audit locally in the same order as CI: uv lock check, requirements freshness, `pip-audit` on both variants, CycloneDX SBOM on both variants. |

### The inner loop

```sh
# Run the CLI
uv run geek42 --help

# Run tests (with coverage)
uv run pytest

# Single test file, verbose
uv run pytest tests/test_linter.py -v

# Single test by name
uv run pytest -k test_parse_format2

# Stop on first failure, drop into pdb
uv run pytest -x --pdb

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run ruff format --check src/ tests/    # CI-style check only

# Type check
uv run ty check

# Security audit of deps
uv export --format requirements-txt --no-emit-project > /tmp/req.txt
uv run pip-audit --strict --desc --requirement /tmp/req.txt
```

### Pre-push checklist

`pre-commit` runs these automatically on `git commit` and `git push`.
To run them manually at any time:

```sh
# Fast CI parity (lint + typecheck + test)
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check
uv run pytest

# Full CI parity (includes supply-chain audit)
uv run pre-commit run --all-files
uv run pre-commit run --all-files --hook-stage pre-push
uv run python scripts/audit.py
```

If these pass locally, CI will pass — pre-commit uses the same
uv-managed binaries as CI.

### Bypassing pre-commit (emergency only)

```sh
git commit --no-verify -S -s -m "chore: emergency hotfix"
git push --no-verify
```

Never bypass to suppress a real failure — fix the failure. Bypass is
only justified when the hook itself is broken (e.g., network outage
preventing `uv` cache) and the commit itself is trivial.

### Adding a dependency

```sh
# Production
uv add pydantic-settings

# Development only
uv add --dev mypy-extensions

# Regenerate the exported requirements files
uv run python scripts/regen_requirements.py

# Commit everything together
git add pyproject.toml uv.lock requirements.txt requirements-dev.txt
git commit -S -s -m "chore(deps): add pydantic-settings"
```

`uv.lock`, `requirements.txt`, and `requirements-dev.txt` **must all
be committed** with every dependency change. The pre-commit
`regen-requirements` hook does this automatically when `pyproject.toml`
or `uv.lock` changes — but if pre-commit isn't installed, run the
regen script manually.

### Why commit requirements.txt AND uv.lock?

Different tools expect different formats:

- `uv.lock` is the source of truth — uv reads it for `uv sync`
- `requirements.txt` (hash-pinned, prod only) — consumable by any
  pip-based toolchain, reviewable in PR diffs, used by `pip-audit`,
  `cyclonedx-py`, and downstream security scanners
- `requirements-dev.txt` (hash-pinned, prod + dev) — same, with
  dev tools included so dev-env vulns are tracked too

Committing all three means:

1. PRs show dependency changes in a reviewable diff format
2. Security scanners can read either `requirements*.txt` or `uv.lock`
3. CI verifies they stay in sync (any drift fails the audit job)

### Updating dependencies

```sh
uv lock --upgrade                        # update all
uv lock --upgrade-package pydantic       # update one

# Always regen after upgrading
uv run python scripts/regen_requirements.py
```

Dependabot runs weekly and will open grouped PRs for routine updates.
The pre-commit hook runs `regen_requirements.py` automatically when
its PRs touch `pyproject.toml` or `uv.lock`, so dependabot branches
stay consistent.

### Running the full audit locally

```sh
uv run python scripts/audit.py
```

This runs all six checks (uv lock consistency, requirements freshness,
pip-audit on prod, pip-audit on prod+dev, SBOM prod, SBOM prod+dev)
and writes reports to `.reports/audit/`. The exact same logic runs
in CI via the `audit` job — if this passes locally, CI will pass.

---

## Semantic commits (Conventional Commits)

**Every commit in geek42 must follow [Conventional Commits](https://www.conventionalcommits.org/).**

### Format

```
<type>(<optional-scope>): <subject>

<optional body>

<optional footer(s)>
```

Rules:

- Subject line ≤ 72 characters, imperative mood, no trailing period
- Body wraps at 72 characters, separated from subject by a blank line
- Footers use `Key: value` format (e.g., `Signed-off-by:`,
  `BREAKING CHANGE:`, `Refs: #123`)
- Every commit is **signed** (see [CONTRIBUTING.md](../CONTRIBUTING.md))
  and **signed off** (`git commit -s`)

### Types (in order of frequency)

| Type | When to use | SemVer impact |
|------|-------------|---------------|
| `feat` | A new user-visible feature | **minor** bump |
| `fix` | A bug fix | **patch** bump |
| `docs` | Docs-only change | none |
| `test` | Adding/fixing tests only | none |
| `refactor` | Code change that's neither a feature nor a fix | none |
| `perf` | Performance improvement | patch |
| `style` | Whitespace, formatting, no logic change | none |
| `chore` | Tooling, dependencies, non-user-visible housekeeping | none |
| `ci` | CI/CD configuration | none |
| `build` | Build system / packaging | none |
| `security` | Security-relevant fix (often also `fix` or `feat`) | patch or minor |

### Scopes (suggested)

Use the module or subsystem name: `parser`, `linter`, `cli`,
`compose`, `tracker`, `site`, `feeds`, `renderer`, `ci`, `deps`,
`docs`, `release`, `templates`.

### Examples

Good:

```
feat(cli): add read-new command

Add `geek42 read-new` which reads all unread items sequentially
and marks each as read. Mirrors `eselect news read new`.

Refs: #12
Signed-off-by: Jane Doe <jane@example.org>
```

```
fix(linter): stop flagging empty body when file ends without newline

Previously the parser's split-on-\n produced an empty trailing
element that was treated as a blank body. Now we rstrip before
splitting.

Fixes: #34
Signed-off-by: Jane Doe <jane@example.org>
```

```
security(site): resolve git executable via shutil.which

Pin the git binary to an absolute path at import time to mitigate
PATH hijacking and satisfy the S607 ruff rule. Raises RuntimeError
immediately if git is missing rather than at first subprocess call.

Signed-off-by: Jane Doe <jane@example.org>
```

```
chore(deps): bump pydantic from 2.12.5 to 2.13.0

Signed-off-by: dependabot[bot] <noreply@github.com>
```

Bad:

```
update stuff                          # no type, no scope, vague
fix: broken                            # subject is meaningless
feat(cli): Added read-new command.     # past tense + trailing period
FIX(CLI): read new                     # uppercase type
fix(cli): added read-new command and fixed unrelated bug in linter
# ^ one commit, two unrelated changes — split into two
```

### Breaking changes

Breaking changes get a `!` after the type/scope AND a
`BREAKING CHANGE:` footer:

```
feat(cli)!: rename `list` command to `ls`

BREAKING CHANGE: `geek42 list` is now `geek42 ls`. Update scripts
that invoked the old name.

Signed-off-by: Jane Doe <jane@example.org>
```

This triggers a **major** version bump on release.

### Rebase vs merge

- **Rebase** feature branches onto `main` before opening a PR, so
  commits are linear and each is independently meaningful.
- **No merge commits on main** — branch protection enforces linear
  history.
- If a PR has cleanup commits like `fix lint` or `address review`,
  squash them into the parent commit via `git rebase -i` before
  merging.

### Automatic changelog

Because every commit follows the convention, `CHANGELOG.md` can be
generated (or validated) mechanically:

```sh
# List all features since the last tag
git log v0.1.0..HEAD --pretty='%s' | grep -E '^feat'

# Extract breaking changes
git log v0.1.0..HEAD --pretty='%B' | grep -A2 'BREAKING CHANGE'
```

### Enforcement

CI checks commit message format on every PR (see
[CI pipeline](#ci-pipeline) below). Badly formatted messages block
the merge.

---

## CI pipeline

On every push to `main` and every PR, the following workflows run in
parallel:

### `ci.yml` — core build

| Job | Runtime | Purpose |
|-----|---------|---------|
| `pre-commit` | ~2 min | Runs `pre-commit run --all-files` — the full hook suite |
| `lint` | ~1 min | `ruff check` (full rule set) with SARIF, JSON, and text output |
| `security-lint` | ~1 min | `ruff check --select S,BLE,TRY` isolated security-only scan |
| `typecheck` | ~1 min | `ty check` |
| `audit` | ~2 min | `pip-audit` + CycloneDX SBOM + `uv lock --check` |
| `osv-scan` | ~2 min | Google OSV-Scanner, second opinion on CVEs |
| `test` | ~3 min | `pytest` with JUnit XML, coverage XML/HTML, PR annotations, coverage badge |

All jobs:

- Run on ubuntu-latest (pinned via matrix)
- Wrap with `step-security/harden-runner` (egress audit)
- Use `persist-credentials: false` on checkout
- Use `uv sync --frozen --dev` for reproducible installs
- Have `timeout-minutes` set
- Grant only `contents: read` (deny-all default at workflow level)

### `codeql.yml` — SAST

Runs the CodeQL analyzer with `security-extended` + `security-and-quality`
query suites for Python. Posts findings to the Security tab. Also runs
weekly on a schedule.

### `scorecard.yml` — OpenSSF Scorecard

Runs weekly plus on every push to `main`. Publishes results to the
public Scorecard API and to the Security tab. Target: ≥ 7/10.

### `gitleaks.yml` — secret scan

Scans the full git history on every push and PR using
`gitleaks/gitleaks-action`. Allowlist lives in `.gitleaks.toml`.

### `dependency-review.yml` — dependency diff

Runs on PRs only. Fails on any dependency introduction with
moderate+ vulnerabilities or forbidden licenses (GPL-2/3, AGPL).
Posts a summary comment on the PR.

### Required status checks

Branch protection on `main` requires these checks to pass before
merge (configure via `docs/security-setup.md`):

- `pre-commit`
- `Lint & format`
- `Security lint (S rules)`
- `Type check`
- `Dependency audit`
- `OSV scan`
- `Test (Python 3.13)`
- `CodeQL (python)`
- `Secret scan`
- `Review dependency changes`

### CI artifacts & reports

Every CI run uploads a set of machine-readable reports and human-readable
logs. They are accessible from the **Actions → workflow run → Artifacts**
section at the bottom of the run page, and retained per the schedule
below.

| Artifact | Contents | Retention | Produced by |
|----------|----------|-----------|-------------|
| `lint-logs` | `ruff.sarif`, `ruff.json`, `ruff.log`, `ruff-format.log` | 14 days | `lint` |
| `security-lint-logs` | `ruff-security.sarif`, `ruff-security.json`, `ruff-security.log` | **30 days** (audit) | `security-lint` |
| `typecheck-log` | `ty.log` | 14 days | `typecheck` |
| `dependency-audit` | `requirements-audit.txt`, `pip-audit.log`, `pip-audit.json`, `sbom.cdx.json` | **90 days** (compliance) | `audit` |
| `osv-scan-report` | `osv-results.sarif` | 30 days | `osv-scan` |
| `test-results-3.13` | `test-results.xml` (JUnit), `coverage.xml` (Cobertura), `htmlcov/`, `pytest.log` | 14 days | `test` |
| `coverage-report-3.13` | `coverage.xml`, `htmlcov/` | 14 days | `test` |
| `scorecard-results` | `scorecard-results.sarif` | 7 days | `scorecard.yml` |

### PR annotations & inline feedback

The following CI outputs create inline comments or annotations on PRs
without any manual setup:

| Source | Mechanism | What you see |
|--------|-----------|--------------|
| **Ruff SARIF** | `github/codeql-action/upload-sarif` with `category: ruff` | Code scanning alerts in PR review, inline with the offending line |
| **Security-only SARIF** | `upload-sarif` with `category: ruff-security` | Tracked separately so security trends can be measured |
| **OSV-Scanner SARIF** | `upload-sarif` with `category: osv-scanner` | Vulnerable dependency annotations on `pyproject.toml` / `uv.lock` |
| **CodeQL SARIF** | `github/codeql-action/analyze` | Deep SAST findings in Security tab + PR |
| **Pytest JUnit XML** | `EnricoMi/publish-unit-test-result-action` | Check summary on the PR with pass/fail counts; individual failures expanded |
| **Coverage XML** | `py-cov-action/python-coverage-comment-action` | A sticky PR comment showing coverage + per-file diff vs. base |
| **pip-audit / SBOM** | Custom `$GITHUB_STEP_SUMMARY` in the `audit` job | Formatted markdown summary in the Actions run page |
| **Test summary** | Custom `$GITHUB_STEP_SUMMARY` in the `test` job | Totals + line/branch coverage percentages |
| **Dependency review** | `actions/dependency-review-action` | PR comment with diff of added/removed/updated deps |
| **Gitleaks** | `gitleaks/gitleaks-action` | Fails the job and annotates the commit on secret detection |

### Coverage badge

The coverage badge in the README is driven by
[`py-cov-action/python-coverage-comment-action`](https://github.com/py-cov-action/python-coverage-comment-action).
On each push to `main` it:

1. Parses `coverage.xml`
2. Computes line & branch coverage
3. Updates an orphan branch `python-coverage-comment-action-data` in
   this repo with a shields.io-compatible `endpoint.json` and a
   `badge.svg`
4. On PRs, posts a sticky comment showing coverage diff vs. the base

No third-party service is involved — the badge is self-hosted inside
this repository. If you prefer Codecov or Coveralls, see
[alternatives](#coverage-badge-alternatives) below.

The badge URL in the README points at the raw SVG on the orphan branch:

```markdown
[![Coverage](https://raw.githubusercontent.com/IvanAnishchuk/geek42/python-coverage-comment-action-data/badge.svg)](...)
```

Thresholds (configured in the CI step):

- **Green** ≥ 90%
- **Orange** 75–89%
- **Red** < 75%

### Coverage badge alternatives

| Option | Pros | Cons |
|--------|------|------|
| `py-cov-action` (current) | Self-hosted, no third party, PR comments + badge, free | Requires orphan branch; slightly more setup |
| [Codecov](https://about.codecov.io/) | Most widely adopted, rich UI, trend graphs, sunburst views | Third-party service trust, past incidents, rate limits for OSS |
| [Coveralls](https://coveralls.io/) | Mature, free for OSS | Third-party, less actively developed |
| [Shields.io endpoint](https://shields.io/endpoints) + Gist | Full control, static SVG | Requires manual gist + PAT wiring |
| [CodeClimate](https://codeclimate.com/) | Quality + coverage in one | Third-party, mostly paid |

### Other badges on the README

| Badge | Source | Updates on |
|-------|--------|------------|
| **CI** | `workflows/ci.yml/badge.svg` | Every run |
| **Coverage** | `python-coverage-comment-action-data` branch SVG | Push to `main` |
| **Tests** | `shields.io/github/actions/workflow/status` | Every run |
| **CodeQL** | `workflows/codeql.yml/badge.svg` | Every run |
| **Scorecard** | `api.scorecard.dev` | Weekly |
| **OpenSSF Best Practices** | `bestpractices.dev/projects/XXXX/badge` | Self-assessment updates |
| **SLSA Level 3** | Static `slsa.dev/images/gh-badge-level3.svg` | Manual (verify after first release) |
| **PyPI** | `shields.io/pypi/v/geek42` | PyPI release |
| **Python versions** | `shields.io/pypi/pyversions/geek42` | PyPI release |
| **Downloads** | `shields.io/pypi/dm/geek42` | PyPI daily |
| **uv / ruff** | Static `raw.githubusercontent.com/astral-sh/*/badge.json` | Upstream |
| **Conventional Commits** | Static `shields.io/badge` | Never |
| **pre-commit** | Static `shields.io/badge` | Never |
| **License** | Static | Never |

### Viewing reports locally

```sh
# HTML coverage
uv run pytest
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux

# JUnit XML pretty-printer
uv run pytest
xmllint --format test-results.xml | less

# SARIF viewer
# VS Code: install the "Sarif Viewer" extension, open any .sarif file
uv run ruff check --output-format=sarif --output-file=ruff.sarif src/

# CycloneDX SBOM dump
uv export --format requirements-txt --no-emit-project > /tmp/req.txt
uv run cyclonedx-py requirements /tmp/req.txt \
    --output-format json --output-file /tmp/sbom.json
jq '.components[] | "\(.name)@\(.version)"' /tmp/sbom.json
```

### Downloading CI artifacts

```sh
# List runs
gh run list --workflow=ci.yml

# Download all artifacts from the most recent run
gh run download

# Download a specific artifact
gh run download --name dependency-audit
gh run download --name test-results-3.13
```

### Custom PR annotations from scripts

If a tool outputs diagnostics that no existing action handles, use
GitHub's [workflow command
format](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions)
to emit inline annotations:

```bash
echo "::error file=src/geek42/parser.py,line=42,col=8::Unused variable 'x'"
echo "::warning file=docs/devops.md,line=100::Line too long"
echo "::notice::Build completed in 30s"
```

These appear inline in the PR **Files changed** view and in the
Actions run page.

---

## Release process

Releases are triggered by pushing a signed tag matching `v*.*.*`.

### 1. Decide the version bump

Based on the semantic commits since the last release:

- Any commits with `BREAKING CHANGE:` or `feat!:`/`fix!:` → **major**
- Any `feat:` commits → **minor**
- Only `fix:`, `perf:`, `security:` → **patch**
- Only `docs:`, `test:`, `chore:`, `ci:`, `build:`, `refactor:` → no
  release needed (or: patch if user-visible)

### 2. Prepare the release commit

```sh
# Update the version
sed -i 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml
sed -i 's/__version__ = "0.1.0"/__version__ = "0.2.0"/' src/geek42/__init__.py

# Update CHANGELOG.md: move [Unreleased] contents to [0.2.0] - YYYY-MM-DD
$EDITOR CHANGELOG.md

# Regenerate the lock file (version bump is a pyproject change)
uv lock

# Commit
git add pyproject.toml src/geek42/__init__.py CHANGELOG.md uv.lock
git commit -S -s -m "chore(release): 0.2.0"

# Open PR, wait for green CI, merge
```

### 3. Tag and push

Once the release commit is on `main`:

```sh
git checkout main
git pull --ff-only

git tag -s v0.2.0 -m "geek42 0.2.0"
git push origin v0.2.0
```

The tag must be **signed** (`-s`). Branch protection does not apply to
tags by default, but the release workflow will reject unsigned tags.

### 4. Watch the release pipeline

`.github/workflows/release.yml` triggers on the tag. Stages:

1. **build** — reproducible wheel + sdist, SBOM, sigstore signing,
   build-provenance attestation, SBOM attestation
2. **provenance** — SLSA L3 generator in an isolated reusable workflow
3. **publish-pypi** — waits for reviewer approval in `pypi` environment,
   then uploads via OIDC trusted publishing (no token)
4. **github-release** — creates the GitHub Release with all artifacts
   attached

Approve the `pypi` environment gate when prompted. The full pipeline
takes ~5-10 minutes.

### 5. Post-release verification

After the release is published:

```sh
# Verify the sigstore bundle
gh release download v0.2.0 --repo IvanAnishchuk/geek42
uv tool run sigstore verify identity \
    --cert-identity-regexp '^https://github\.com/IvanAnishchuk/geek42/\.github/workflows/release\.yml@' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    --bundle geek42-0.2.0-py3-none-any.whl.sigstore \
    geek42-0.2.0-py3-none-any.whl

# Verify the attestation
gh attestation verify geek42-0.2.0-py3-none-any.whl --owner IvanAnishchuk

# Verify SLSA provenance
slsa-verifier verify-artifact \
    --provenance-path geek42-provenance.intoto.jsonl \
    --source-uri github.com/IvanAnishchuk/geek42 \
    --source-tag v0.2.0 \
    geek42-0.2.0-py3-none-any.whl

# Install from PyPI and smoke test
pip install geek42==0.2.0
geek42 --version
geek42 --help
```

### 6. Announce

- Post on the project's mailing list / forum / Mastodon
- Update OpenSSF Best Practices badge if criteria changed

### Dry-run releases via TestPyPI

Before cutting a real release, you can test the pipeline via
`workflow_dispatch`:

```sh
gh workflow run release.yml -f testpypi=true
```

This runs the full pipeline up to the `publish-testpypi` job and
uploads to `https://test.pypi.org/project/geek42/`. Useful after
major changes to the release workflow itself.

---

## Reproducible builds

geek42 produces **byte-identical** wheels for the same source and
`SOURCE_DATE_EPOCH`. This enables third-party verification.

### How it works

1. `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)` — set from the tag
   commit timestamp. All file mtimes and wheel metadata use this.
2. `PYTHONHASHSEED=0` — deterministic hash seed for any build-time
   dict ordering.
3. Hatchling's wheel builder uses sorted file ordering and strips
   non-reproducible metadata.
4. `uv build` without `--no-sources` ensures local file reads are
   deterministic.

### Verifying reproducibility locally

```sh
# Build twice with the same env
export SOURCE_DATE_EPOCH=1700000000
export PYTHONHASHSEED=0

rm -rf dist
uv build
sha256sum dist/*.whl dist/*.tar.gz > /tmp/hash1

rm -rf dist
uv build
sha256sum dist/*.whl dist/*.tar.gz > /tmp/hash2

diff /tmp/hash1 /tmp/hash2 && echo "REPRODUCIBLE"
```

### Verifying a release is reproducible

```sh
git clone https://github.com/IvanAnishchuk/geek42
cd geek42
git checkout v0.2.0

export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export PYTHONHASHSEED=0
uv build

# Compare to the published wheel
sha256sum dist/*.whl
gh release download v0.2.0 --pattern '*.whl'
sha256sum geek42-0.2.0-py3-none-any.whl
```

The two hashes must match exactly.

---

## Secrets management

**geek42 has no long-lived secrets in GitHub Actions.**

- PyPI: OIDC trusted publisher (no token)
- Sigstore: OIDC keyless signing (no key)
- Build provenance: OIDC attestation (no key)

The only secret in the repo is `GITHUB_TOKEN`, which is auto-scoped
per job via `permissions:` blocks and revoked at the end of each run.

If you ever need to add a secret:

1. Justify it — is there an OIDC-based alternative?
2. Scope it to a specific environment (e.g., `pypi`) with reviewer gate
3. Document its rotation schedule in `docs/security-setup.md`
4. Rotate it after any suspected compromise or maintainer turnover

---

## Debugging CI failures

### Lint / format failures

```sh
uv run ruff check --fix src/ tests/    # auto-fix what can be fixed
uv run ruff format src/ tests/          # apply formatting
```

Commit the fixes with `style:` or `chore:` type.

### Type check failures

Read the ty output carefully — ty prints source context and the
specific rule. Common causes:

- Missing return type annotation → add it
- `Any` leaking into public API → add a proper type
- Dict `.get()` returning `Optional` passed to non-Optional param → handle `None`

### Test failures

```sh
# Reproduce locally
uv run pytest tests/test_foo.py::test_bar -v -s

# With debugger
uv run pytest tests/test_foo.py::test_bar -v -s --pdb

# Show full diff on assertion failure
uv run pytest tests/test_foo.py::test_bar -vv
```

Check coverage regressions:

```sh
uv run pytest --cov-report=term-missing
```

### pip-audit failures

```sh
uv export --format requirements-txt --no-emit-project > /tmp/req.txt
uv run pip-audit --requirement /tmp/req.txt --desc
```

If a vuln has no fix yet, temporarily add `--ignore-vuln VULN-ID`
with an expiration comment, open a tracking issue, and add a
`# FIXME: pip-audit ignore` note in `docs/security.md` incidents log.

### CodeQL failures

View findings in the **Security → Code scanning alerts** tab on
GitHub. Each finding has a description and suggested fix. Address
all high-severity findings immediately; triage medium as
informational unless exploitable.

### Gitleaks false positives

Add the path or regex to `.gitleaks.toml` under `[allowlist]` with a
comment explaining why. Never commit a real secret and then allow-list
it — rotate the secret first.

### Harden-runner alerts

If `harden-runner` reports unexpected egress, it's either:

1. A new action making a network call (read its source, decide if
   legitimate, add to allowed endpoints)
2. A compromised action (bail immediately, file an issue upstream,
   pin to an earlier known-good SHA)

---

## Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SOURCE_DATE_EPOCH` | Build | Reproducible wheel timestamps |
| `PYTHONHASHSEED` | Build | Deterministic dict ordering |
| `VISUAL` / `EDITOR` | `geek42 new`/`revise` | Editor to open |
| `GITHUB_TOKEN` | CI | Auto-scoped per job, never exported |
| `UV_CACHE_DIR` | Local dev (optional) | Shared uv cache location |
| `RUFF_CACHE_DIR` | Local dev (optional) | Shared ruff cache |

---

## FAQ

**Why `uv` instead of pip/poetry/pdm?**

Speed (10–100× faster installs), integrated resolver, lockfile with
hashes, and first-class reproducibility features. We standardize on
`uv run <cmd>` so developers never have to manage a virtualenv.

**Why are actions SHA-pinned instead of tag-pinned?**

Tags are mutable on GitHub. A compromised action repository could
re-point `v4` to a malicious commit and every downstream consumer
would silently inherit it. SHA pins are immutable.

**Why both `sigstore` and `SLSA` provenance?**

They protect against different attacks. Sigstore proves *who* signed
the artifact; SLSA L3 proves *how* it was built in a non-forgeable way
by running the provenance generator in an isolated reusable workflow.
Together they provide end-to-end integrity.

**Why `pypi` environment with manual approval?**

Defense in depth. Even if an attacker compromises a maintainer's
GitHub account and pushes a tag, the release cannot reach PyPI without
another maintainer clicking "Approve" on the environment gate.

**How do I run a single test fast?**

```sh
uv run pytest tests/test_linter.py::test_valid_file_no_errors -x --no-cov
```

The `--no-cov` skips coverage collection.

**How long does a full release take?**

~5–10 minutes from tag push to PyPI availability, gated on the
`pypi` environment approval click.

---

## Links

- [Contributing](../CONTRIBUTING.md)
- [Security policy](../SECURITY.md)
- [Security architecture](security.md)
- [Security setup checklist](security-setup.md)
- [News format reference](news-format.md)
- [Changelog](../CHANGELOG.md)
