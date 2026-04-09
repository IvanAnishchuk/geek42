# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Custom exception hierarchy (`src/geek42/errors.py`):
  `Geek42Error` base with subclasses `ParseError`,
  `MissingHeaderError`, `InvalidHeaderValueError`, `ComposeError`,
  `EmptyTitleError`, `SlugDerivationError`, `ItemNotFoundError`,
  `ConfigError`, `SourceNotFoundError`, `NoSourcesConfiguredError`,
  `SourceNotPulledError`, `SystemDependencyError`, `GitNotFoundError`,
  `EditorFailedError`. Central `main()` now catches `Geek42Error`
  at the CLI boundary.
- Multi-stage `Dockerfile` using `ghcr.io/astral-sh/uv` as builder,
  non-root user, OCI labels, healthcheck. `.dockerignore` provided.
- Debian packaging (`packaging/debian/`): control, rules, changelog,
  copyright, source/format, watch, geek42.manpages. Uses
  `pybuild-plugin-pyproject` with the hatchling backend.
- RPM spec file (`packaging/rpm/geek42.spec`) following Fedora
  Python packaging guidelines with `pyproject-rpm-macros`.
- Gentoo ebuild (`packaging/gentoo/app-text/geek42/*`) with
  `EAPI=8`, `distutils-r1`, hatchling backend, metadata.xml,
  post-install message, Python 3.13 and 3.14 support.
- `packaging/README.md` documenting every downstream format.
- `.github/settings.yml` — managed by the repository-settings GitHub
  App. Declares branch protection, status checks, labels,
  environments, security features — all from a committed file.
- `.github/FUNDING.yml` (placeholder, all commented).
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request,config}.yml`
- `.github/PULL_REQUEST_TEMPLATE.md` with Conventional Commits and
  DCO checklist.
- `scripts/regen_requirements.py` — regenerate hash-pinned
  `requirements.txt` (prod) and `requirements-dev.txt` (prod + dev)
  from `uv.lock`. Both files are now **committed to the repo**.
- `scripts/audit.py` — full supply-chain audit matching CI:
  `uv lock --check`, requirements freshness, `pip-audit` on both
  prod and dev, CycloneDX SBOMs for both variants
- pre-commit `regen-requirements` hook: auto-regenerates
  `requirements*.txt` whenever `pyproject.toml` or `uv.lock` changes
- pre-commit `audit` hook (pre-push stage): runs full audit locally
- `.reports/` directory as the single home for all generated reports,
  caches, and CI artifacts (gitignored). Subdirectories: `lint/`,
  `security-lint/`, `typecheck/`, `audit/`, `test/`, `osv/`
- CI artifacts with structured categories, SARIF uploads for PR
  annotations via GitHub code scanning (ruff, ruff-security, OSV),
  JUnit XML test results, Cobertura coverage XML
- Self-hosted coverage badge via
  `py-cov-action/python-coverage-comment-action` (orphan branch,
  no third-party telemetry)
- Additional README badges: Coverage, Tests, Downloads, uv, ruff,
  Conventional Commits, pre-commit, StepSecurity
- `security-lint` CI job — runs only the `S`, `BLE`, `TRY` rule
  groups and uploads a separate SARIF category so security trends
  can be tracked independently of style
- `osv-scan` CI job — Google's OSV-Scanner as a second-opinion
  vulnerability scanner alongside `pip-audit`
- `pytest --junitxml` and `--cov-report=xml` emitted by default via
  `pyproject.toml` config

### Changed

- Pytest, coverage, and all CI reports now write to `.reports/`
  subdirectories (no more stray `coverage.xml`, `test-results.xml`,
  `htmlcov/` at repo root)
- CI `audit` job now runs `scripts/audit.py` instead of inline bash
- CI uses committed `requirements.txt` / `requirements-dev.txt`
  directly; the audit script verifies they are in sync with `uv.lock`
- Removed bash helper scripts and Makefile in favor of pure Python
  scripts invoked via `uv run`
- **Parser refactor**: `parser.py` now raises `MissingHeaderError`
  and `InvalidHeaderValueError` (subclasses of `ParseError`) with
  full context. `scan_repo` catches `ParseError` and `OSError`
  specifically instead of `Exception`. Required-headers list is
  exported as `REQUIRED_HEADERS`. Dead defaults removed.
- **Compose refactor**: `place_news_item` raises `EmptyTitleError`
  and `SlugDerivationError` instead of raw `ValueError`.
- **Site refactor**: `_require_git` raises `GitNotFoundError` instead
  of `RuntimeError`. Incorrect `collect_items` return-value docstring
  corrected.
- **Renderer fix**: `news_to_markdown` now uses `json.dumps` for
  YAML string escaping, preventing broken frontmatter when titles
  or authors contain double-quotes.
- Removed `TRY003` from ruff ignore list — no longer needed since
  exceptions carry their own messages in `__init__`.

## [0.2.0] - 2026-04-09

### Added

#### Authoring & reading
- `geek42 new` — create a news item from a template in `$EDITOR`, with
  author inferred from git config, auto-linting, and placement into the
  source repo under the derived item ID
- `geek42 revise <id>` — bump revision and posted date, edit in
  `$EDITOR`, auto-lint, write back to the original file
- `geek42 read-new` — read all unread items sequentially, marking each
  as read (equivalent to `eselect news read new`)
- `geek42 list --new` — filter list to unread items only
- Read/unread tracker (`ReadTracker`) persisting to
  `{data_dir}/read.txt`; the `read` command now marks items as read on
  display; `list` shows unread counts and per-row markers
- `src/geek42/compose.py` — editor, template, slug, placement, and
  revision-preparation helpers
- `src/geek42/tracker.py` — read-state persistence

#### Documentation
- `docs/news-format.md` — GLEP 42 format spec, blog maintenance
  workflow, and reader workflow
- `docs/security.md` — supply-chain threat model and verification guide
- `docs/devops.md` — CI/CD and release pipeline reference
- `docs/security-setup.md` — repo-owner configuration checklist for
  branch protection, GHAS, PyPI trusted publishing, and 2FA

#### Supply chain & governance
- `SECURITY.md` — vulnerability disclosure policy with response SLA and
  safe harbor
- `CONTRIBUTING.md` — contribution guide requiring signed commits
  (GPG/SSH/sigstore), DCO sign-off, Conventional Commits
- `.github/CODEOWNERS` — mandatory code-owner review, with extra
  paths flagged for security-sensitive files
- `.github/dependabot.yml` — weekly grouped pip and github-actions
  updates with scoped commit prefixes
- `.gitleaks.toml` — gitleaks config with test/doc allowlist

#### CI / scanning workflows
- `.github/workflows/codeql.yml` — CodeQL SAST with
  `security-extended` and `security-and-quality` query suites,
  scheduled weekly
- `.github/workflows/scorecard.yml` — OpenSSF Scorecard with SARIF
  upload and public publish
- `.github/workflows/gitleaks.yml` — secret scanning on push, PR, and
  schedule
- `.github/workflows/dependency-review.yml` — PR-time dependency diff
  with moderate-severity gate and GPL license denylist

#### Release pipeline
- `.github/workflows/release.yml` — full release pipeline triggered on
  `v*.*.*` tags:
  - Reproducible wheel + sdist build via `SOURCE_DATE_EPOCH` +
    `PYTHONHASHSEED=0`
  - CycloneDX SBOM generation via `cyclonedx-py`
  - GitHub build-provenance attestation
    (`actions/attest-build-provenance`)
  - SBOM attestation (`actions/attest-sbom`)
  - Sigstore keyless signing (`sigstore/gh-action-sigstore-python`)
  - SLSA Level 3 provenance via `slsa-framework/slsa-github-generator`
  - PyPI publishing via **trusted publisher / OIDC** — no tokens
  - Optional TestPyPI path via `workflow_dispatch`
  - GitHub Release creation with all artifacts, signatures, SBOM, and
    provenance attached
- `pypi` environment with required reviewer gate (configured via
  `docs/security-setup.md`)

#### Pyproject hardening
- Ruff security rule groups: `S` (flake8-bandit), `BLE`
  (blind-except), `TRY` (tryceratops)
- New dev dependencies: `pip-audit>=2.7`, `cyclonedx-bom>=4.5`
- PyPI classifiers, `project.urls`, `project.license = CC0-1.0`
- `hatchling>=1.25` minimum for reproducible builds
- `tool.hatch.build.targets.sdist` include list

#### README
- Badges block: CI, CodeQL, OpenSSF Scorecard, OpenSSF Best Practices,
  SLSA Level 3, PyPI version, Python versions, CC0 license
- `## Security` section with verification commands for sigstore,
  GitHub attestations, and SLSA provenance
- Links to new docs

### Changed

- **CI hardening** (`.github/workflows/ci.yml`):
  - All actions SHA-pinned with version comments
  - Top-level `permissions: {}` deny-all, per-job least-privilege grants
  - `step-security/harden-runner` first step in every job (egress audit)
  - `actions/checkout` with `persist-credentials: false`
  - `uv sync --frozen --dev` for reproducible dependency installs
  - New `audit` job running `pip-audit --strict` against exported
    requirements (excluding the project itself)
  - `timeout-minutes` on every job
  - `concurrency` group with `cancel-in-progress` for PRs
- **Security lint fixes** (triggered by new S rules):
  - `src/geek42/site.py` — `git` resolved via `shutil.which("git")` at
    import time, stored as absolute path, fail-fast via `_require_git()`
  - `src/geek42/compose.py` — same pattern for `_git_config`; editor
    subprocess call annotated with justified `# noqa: S603`
  - `src/geek42/linter.py` — replaced blind `except Exception` with
    `OSError` + `UnicodeDecodeError`; refactored revision validation to
    avoid `raise inside try` (TRY301)
- Test suite now covers read/unread tracker, read-new command, list
  --new flag, CLI compose/revise flows, and editor mocking patterns
- Branch coverage + Cobertura XML export enabled
  (`fail_under = 80`, currently at ~94%)

### Security

- Reproducibility verified: two consecutive local builds produce
  byte-identical `.whl` and `.tar.gz` given the same
  `SOURCE_DATE_EPOCH`
- `pip-audit` passes with zero known vulnerabilities across all
  production dependencies
- CodeQL `security-extended` suite enabled
- Trust model: releases require (1) a signed commit on `main`,
  (2) a tag, (3) `pypi` environment reviewer approval, (4) OIDC identity
  match to the release workflow — no long-lived credentials exist

### Documentation migration notes

- `python -m sigstore` commands replaced with `uv tool run sigstore`
  throughout README and SECURITY.md

## [0.1.0] - 2026-04-09

### Added

- GLEP 42 news file parser supporting format 1.0 and 2.0
- Static site generator with Jinja2 templates, semantic HTML,
  Schema.org JSON-LD, and Open Graph
- RSS 2.0 and Atom 1.0 feed generation
- Markdown export with YAML frontmatter
- Multi-source support via `[[sources]]` in TOML config
- Terminal reader with Rich formatting (`list` and `read` commands)
- News file linter with error and warning diagnostics
- Dark mode support via `prefers-color-scheme`
- GitHub Actions CI workflow (ruff, ty, pytest with coverage)
