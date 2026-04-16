# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [PEP 440](https://peps.python.org/pep-0440/) (e.g. `0.4.2a7`
for alpha, `0.4.2b1` for beta, `0.4.2c1` for release candidate).

## [Unreleased]

### Added

- Companion workflow (`dependabot-regen.yml`) that auto-regenerates
  `requirements*.txt` after Dependabot updates dependencies.
- Badge generation script (`scripts/regen_badges.py`) that extracts
  tool versions from `uv.lock` for dynamic shields.io badges (#61).

### Changed

- Switch Dependabot from `pip` to `uv` ecosystem so it updates
  `pyproject.toml` + `uv.lock` directly (#94).
- Fix duplicate scope in Dependabot commit messages (e.g.
  `chore(deps)(deps):` → `chore(deps):`).
- Copilot instructions: clarify that "review" means feedback only,
  not committing fixes on behalf of the author.
- Remove inline PyPI provenance fetching from verify scripts — they
  now read from `proofs/{pypi,testpypi}/` populated by
  `download_release.py` (#48).

### Fixed

- Replace hard-coded tool version badges with dynamic shields.io
  endpoints generated from `uv.lock` (#61).
- Add uv as dev dependency so its version is tracked in `uv.lock`.
- Distinguish 404 (no attestation) from network/server errors in
  `download_release.py`'s `fetch_pypi_provenance` (#48).
- Guard `stderr.splitlines()[-1]` against empty/whitespace-only stderr
  to prevent `IndexError` crash in verify scripts (#50).
- Publisher mismatch in verify_provenance.py now fails closed instead
  of warning and continuing (#71).
- Tighten cosign identity regexp to match only the release workflow,
  not any workflow in the repo (#71).
- Wrap trust anchor derivation from pyproject.toml in try/except with
  clear error messages across all verify/download scripts (#71).
- Catch `ValueError` (covers `binascii.Error`) in SLSA provenance
  base64 decoding to prevent crash on malformed payloads (#56).

## [0.4.2a9] - 2026-04-12

### Fixed

- Revert SLSA generator to tag ref (`@v2.1.0`) — commit SHA pinning
  breaks `generate-builder.sh` which requires `refs/tags/vX.Y.Z`.
  Accepted exception to SHA-pinning policy: reusable workflow runs
  in an isolated environment and provenance is independently verifiable.

## [0.4.2a8] - 2026-04-12

### Added

- Gemini Code Assist and CodeRabbit as PR reviewers with
  repo-level configuration (#46).

### Changed

- Derive trust anchors (repo slug, package name, OIDC issuer) from
  `pyproject.toml` instead of hardcoding in verify scripts (#37).
- Add `RELEASE_WORKFLOW` and `TAG_PREFIX` constants for configurability.
- Pin `slsa-github-generator` to commit SHA (#49).
- Replace versioned ebuilds with single `-9999` live ebuild that
  supports both git and PyPI via PV conditional. Add `gen_ebuild.py`
  script to generate versioned copies at release time (#55).

### Fixed

- Replace deprecated `deny-licenses` with `allow-licenses` allowlist
  in dependency-review workflow. Expand license policy to include
  copyleft (GPL, LGPL, MPL) and public domain (WTFPL) alongside
  permissive licenses.
  Enable `retry-on-snapshot-warnings` and `show-openssf-scorecard`
  to fix empty scan results (#76).

## [0.4.2a7] - 2026-04-12

### Added

- `download_release.py` — downloads from GitHub Release, GitHub
  Attestation API, and PyPI/TestPyPI Integrity API. Extracts all
  proof formats (`.publish.attestation`, cosign bundles, GH attestation
  bundles) into `proofs/` subdirectories (#35).
- `verify_cosign.py` — single-binary verification using cosign for all
  five supply-chain providers (#29).
- `verify_pure.py` — pure-Python verification using sigstore and
  pypi-attestations libraries (#29).
- Trust chain display on successful verification (#34).
- `pypi-attestations` CLI integration for PEP 740 verification in
  `verify_provenance.py` (`inspect` + `verify attestation`) (#36).
- `docs/pypi-attestations-cli-research.md` — CLI research findings.
- `docs/attestation-verification.md` — state-of-the-art guide for
  package attestation verification.
- CLAUDE.md and copilot-instructions.md for AI-assisted development.

### Changed

- `verify_provenance.py` uses `pypi-attestations` CLI instead of
  Python library imports for PEP 740 verification (#36).
- Format conversions (GH attestation bundles, cosign-compatible PEP 740
  bundles) moved from verify scripts into `download_release.py` (#35).
- Proof files stored in per-index directories (`proofs/pypi/`,
  `proofs/testpypi/`) instead of mixed `proofs/pypi/` with prefixed
  filenames.
- Uniform hash display across all verification scripts (#33).

### Fixed

- Verify artifact hash against SLSA provenance subjects.
- All `# noqa` suppressions audited and documented (#41).
- Versioned filenames for SBOM, SHA256SUMS, and provenance files.

## [0.4.2a6] - 2026-04-11

### Added

- Real cryptographic PEP 740 verification via `pypi-attestations`
  library in `verify_provenance.py`.

### Changed

- Verify `dist/` files directly instead of downloading duplicates.
- Proofs organized into `proofs/github/` and `proofs/pypi/` subdirs.

## [0.4.2a5] - 2026-04-11

### Fixed

- Create draft release before publishing for immutability.
- Use explicit `*.sigstore.json` glob for release assets.

## [0.4.2a4] - 2026-04-11

### Fixed

- Enable SLSA L3 provenance (`contents: write` permission fix).

## [0.4.2a3] - 2026-04-11

### Fixed

- Only allow merge commits in repo settings.
- Remove deployment branch policies from environments.

## [0.4.2a2] - 2026-04-11

### Fixed

- Handle all PEP 440 pre-release suffixes (a/b/c/dev) in CI routing.
- Simplify environment deployment branch policies.

## [0.4.2a1] - 2026-04-11

### Changed

- Switch to unified `actions/attest@v4.1.0` for build provenance and
  SBOM attestations (replaces `attest-build-provenance` + `attest-sbom`).
- Add `attestations: write` permission to publish jobs for PEP 740
  publish attestations.
- Route dev/rc version tags to TestPyPI instead of PyPI.
- Enable all README badges (PyPI, coverage, release, tooling versions,
  attestations).

## [0.4.1] - 2026-04-11

### Fixed

- Re-enable attestations (`attestations: write`) in release workflow
  (confirmed working via dev-test branch).
- Temporarily disable SLSA L3 provenance — the
  `slsa-framework/slsa-github-generator` reusable workflow causes
  `startup_failure`. Will investigate and re-enable separately.
- Remove SLSA provenance from publish/release dependency chain so
  releases can proceed.

## [0.4.0] - 2026-04-10

### Added

- **`--directory` / `-C` option** on all commands (`init`, `pull`,
  `build`, `list`, `read`, `read-new`, `new`, `revise`). When given,
  the config file, `data_dir`, and `output_dir` are resolved relative
  to that directory, and local sources scan it instead of the current
  working directory. `geek42 new -C <dir>` places the news item
  directly in `<dir>`, bypassing source resolution — this fixes the
  "source has not been pulled" error when running from inside a news
  repo that only has a remote source configured.
- **`metadata/news/` default layout**: news items are now stored
  under `metadata/news/` (the standard portage repository layout).
  `scan_repo`, `find_item_file`, `lint_repo`, and `compile_news`
  auto-detect `metadata/news/` if present, falling back to the repo
  root for dedicated news-only repos (e.g. `glep42-news-gentoo.git`).
  `place_news_item` always writes to `metadata/news/`.
- **`resolve_news_root`** helper and **`NEWS_SUBDIR`** constant
  exported from the public API.
- **`geek42 commit`** — stages news items, runs `compile-blog`, and
  commits with an auto-generated Conventional Commits message (like
  `pkgdev commit`). Accepts `-m` to override the message.
- **`geek42 push`** — pushes commits to the remote.
- **`geek42 deploy-status`** — checks GitHub Pages deployment and
  latest CI run status on main (requires `gh` CLI).
- **`geek42 init` full scaffold** — now creates a complete news
  repository matching Gentoo overlay conventions: `metadata/news/`,
  `.pre-commit-config.yaml` (text hygiene, yamllint, mdformat,
  gemato-sign, geek42 lint/compile-blog), `.github/workflows/`
  (lint, manifest verification, deploy), `.github/dependabot.yml`,
  `.yamllint.yml`, `pyproject.toml` (dev deps), `README.md` (with
  index markers), `.gitignore`, `metadata/layout.conf`. Use `--bare`
  for config-only mode. Accepts `--title`.
- **`geek42 sign`** — regenerates the gemato Manifest tree using
  `gemato create/update --profile ebuild` (same hierarchical
  structure as the Gentoo portage tree). Signs with `--key` or
  `signing_key` from `geek42.toml`.
- **`geek42 verify`** — verifies the Manifest tree via `gemato
  verify` (with `--require-signed-manifest` when
  `metadata/key.asc` is present).
- **`signing_key`** optional field in `SiteConfig` / `geek42.toml`.
- **`scaffold` module** (`scaffold.py`) with the full template set.
- **`manifest` module** (`manifest.py`) with `generate_manifest`
  and `verify_manifest` (delegates to gemato).
- **`GematoNotFoundError`** exception (gemato is required for
  Manifest operations).
- **Testing policy** (`docs/testing-policy.md`), **style guide**
  (`docs/style-guide.md`), **user guide** (`docs/user-guide.md`),
  **OpenSSF Best Practices answers**
  (`docs/openssf-best-practices.md`), **release setup checklist**
  (`docs/release-setup.md`).

### Changed

- **`cyclonedx-bom` moved to `uv tool run`** — no longer a dev
  dependency, avoiding chardet version conflicts.

## [0.3.0] - 2026-04-10

### Added

- **Local-first workflow**: the default source is now `url = "."` (the
  current directory). `geek42 init` creates a config for a local news
  blog; `geek42 new` and `geek42 revise` work directly in the repo
  without requiring `geek42 pull`. Remote sources remain fully
  supported by adding `[[sources]]` entries with git URLs.
- **`geek42 compile-blog` command**: compiles all GLEP 42 news items
  into Markdown files in `news/` and updates a news index in
  `README.md`. Designed to run as a pre-commit hook so the git repo
  itself is a readable blog.
- **`NewsSource.is_local` property**: True when `url == "."`, used
  throughout to skip git operations for local sources.

### Changed

- **Default config**: `geek42 init` now generates a config with
  `url = "."` (local source) and infers the author from git config,
  instead of pointing at the Gentoo news repository.
- **`pull` / `build`**: skip local sources during pull; `collect_items`
  scans the current directory for local sources instead of
  `data_dir/repos/`.
- **`find_item_file`** (compose): resolves local sources to the current
  directory, enabling `geek42 revise` without prior pull.

- **Public API surface**: `src/geek42/__init__.py` now re-exports the
  full public API (`NewsItem`, `NewsSource`, `SiteConfig`, all
  exception classes, `parse_news_file`, `scan_repo`, `lint_news_file`,
  `lint_repo`, `generate_rss`, `generate_atom`, `body_to_html`,
  `news_to_markdown`, `write_markdown`, `ReadTracker`, `Diagnostic`,
  `Severity`, `__version__`) with `__all__` declared. Importing from
  `geek42` is now the supported entry point.
- **Pydantic field descriptions**: every field on `NewsItem`,
  `NewsSource`, and `SiteConfig` now has `Field(..., description=...)`
  so `model_json_schema()` produces useful schemas.
- **`feeds.MAX_FEED_SUMMARY_LEN` constant** replacing the magic
  number `500` previously hard-coded in two places.
- **Tests** for previously uncovered exception paths:
  `MissingHeaderError`, `InvalidHeaderValueError` (Posted, Revision),
  `GitNotFoundError` (via `monkeypatch.setattr(site, "_GIT", None)`).
  Test count: 119 → 125; coverage 94.3% → 95.4%.

### Changed

- **`cli._run_editor_loop`**: extracted the duplicated edit-and-lint
  loop from `cli.new` and `cli.revise` into a single helper. The
  helper raises `EditorFailedError` (previously inline `typer.Exit`)
  on editor failure, so it now flows through the central
  `Geek42Error` boundary in `cli.main()`.
- **`compose.find_item_file`**: type annotation tightened from
  `sources: list` to `sources: list[NewsSource]`, fixing a silent
  type-checker hole.
- **Public-API docstrings** filled in for `ReadTracker` (class +
  every method), `feeds.generate_rss`, `feeds.generate_atom`,
  `feeds._to_datetime`, `feeds._xml_to_str`, `compose.find_item_file`,
  `compose.get_editor`, `compose.infer_author`, `compose.title_to_slug`,
  `compose.generate_template`, `compose.make_temp_copy`,
  `compose.prepare_revision`, and `renderer.write_markdown`.
- **`feeds._to_datetime`** now uses `datetime.combine(date, time.min,
  tzinfo=UTC)` instead of `datetime(year, month, day, tzinfo=UTC)`.
- **`parser.py`**: `Content-Type` lookup uses an explicit
  `if "Content-Type" in headers else None` instead of the awkward
  `headers.get("Content-Type", [None])[0]` pattern.
- **`compose.generate_template`**: removed pointless `f` prefix on
  string literals that had no interpolation.
- **`cli.py`**: `import shutil` moved from inside `revise()` to the
  module top, matching the rest of the imports.

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
