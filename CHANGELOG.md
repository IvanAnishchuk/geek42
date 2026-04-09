# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
