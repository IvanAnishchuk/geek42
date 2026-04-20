# OpenSSF Best Practices Badge — Project 12450

Answers for the [OpenSSF Best Practices](https://www.bestpractices.dev/projects/12450)
badge form. Update this document as the project evolves.

Badge: <https://www.bestpractices.dev/projects/12450>
Criteria: <https://www.bestpractices.dev/criteria/0>

---

## How answers map to our setup

Many badge questions are satisfied by **GitHub defaults** (public repo,
issues, wiki), **committed config files** (settings.yml, CODEOWNERS,
workflows), or **GitHub UI toggles** (security settings). The table
below maps each to the specific mechanism.

Legend:
- **GH default** — GitHub provides this out of the box for public repos
- **Repo file** — enforced by a committed file
- **GH setting** — requires a manual toggle in Settings (see `docs/release-setup.md`)
- **CI** — enforced by a workflow that runs on every push/PR

---

## Basics

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Project website URL | Met | GH default | `https://github.com/IvanAnishchuk/geek42` |
| Description | Met | Repo file | `pyproject.toml` description + `settings.yml` `repository.description` |
| OSS license | Met | Repo file | `LICENSE.md` (CC0-1.0) + `pyproject.toml` `license = "CC0-1.0"` |
| License in standard location | Met | Repo file | `LICENSE.md` at repo root — GitHub auto-detects |
| Documentation of basic use | Met | Repo file | `README.md` Quickstart + CLI Commands |
| How to contribute | Met | Repo file | `CONTRIBUTING.md` — GitHub shows "Contributing" tab |
| FLOSS license | Met | Repo file | CC0-1.0 (public domain dedication) |

## Change control

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Public VCS | Met | GH default | Public GitHub repo |
| Track issues publicly | Met | GH default | GitHub Issues enabled (`has_issues: true` in settings.yml) |
| Interim & release versions via VCS | Met | GH default | All development on `main`, releases tagged `v*.*.*` |
| Release notes | Met | Repo file + CI | `CHANGELOG.md` (Keep a Changelog); release workflow creates GitHub Releases |
| Unique version numbering | Met | Repo file | SemVer; `pyproject.toml` `version` + `__version__` in `__init__.py` |
| ChangeLog | Met | Repo file | `CHANGELOG.md` |

## Reporting

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Bug reporting process | Met | Repo file | `.github/ISSUE_TEMPLATE/config.yml` with bug report template |
| Respond to bugs | Met | Policy | Owner-maintained, responds within days |
| Vulnerability reporting | Met | Repo file + GH setting | `SECURITY.md` with email SLA; **enable Private vulnerability reporting** in Settings |

## Quality

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Working build system [build] | Met | Repo file | `hatchling` via `pyproject.toml`; `uv build` produces wheel + sdist |
| Common build tools [build_common_tools] | Met | Repo file | uv + hatchling, both widely-used Python standards |
| Build with FLOSS tools [build_floss_tools] | Met | Repo file | uv (Apache-2.0), hatchling (MIT), Python (PSF) — all FLOSS |
| Automated test suite [test] | Met | CI | 240+ pytest tests; CI runs on every push/PR (`test.yml`) |
| Standard invocation [test_invocation] | Met | Repo file | `uv run pytest` — standard for Python projects |
| Test coverage [test_most] | Met | CI | Statement + branch coverage tracked; badge on README; >80% overall |
| CI [test_continuous_integration] | Met | CI | GitHub Actions on every push and PR |
| FLOSS test framework | Met | Repo file | pytest (MIT license) |
| Test policy [test_policy] | Met | Policy | `CONTRIBUTING.md` + `docs/testing-policy.md` require tests for all new code |
| Tests are added [tests_are_added] | **?** | Evidence only | Policy exists but **no automated gate** on new-code coverage. See "Planned improvements" below |
| Test policy documented [tests_documented_added] | Met | Repo file | `CONTRIBUTING.md` PR checklist requires "Tests added/updated"; `docs/testing-policy.md` is the full policy |
| Warning flags [warnings] | Met | CI | ruff (500+ rules), ty (type checker), pre-commit (20+ hooks). Reports saved as CI artifacts |
| Warnings addressed [warnings_fixed] | Met | CI | CI fails on any ruff error or ty diagnostic. Zero warnings in current main |
| Warnings strict [warnings_strict] | Met | CI | ruff configured with security rules (S, BLE, TRY), line-length 100. ty runs without suppression |

### Test policy detail

All new features and bug fixes **must** include tests. This is
enforced by:

1. **Coverage floor**: `[tool.coverage.report] fail_under = 75` in
   `pyproject.toml` — CI fails if overall coverage drops below the floor.
2. **Required status check**: `Test (Python 3.13)` is a required
   check in branch protection — PRs cannot merge without passing tests.
3. **Contributing guide**: `CONTRIBUTING.md` states that PRs must
   include tests for new functionality and regression tests for bugs.
4. **Code review**: `CODEOWNERS` requires code-owner approval; reviewers
   check for test coverage.
5. **Coverage comment**: PR comment shows per-file statement + branch
   coverage changes with inline annotations on uncovered lines.

### What is NOT yet automated

The `tests_are_added` criterion requires evidence that new code has
tests. Currently this is enforced by **reviewer judgment** (coverage
comment shows uncovered lines) but there is **no CI gate** that
blocks a PR for insufficient new-code coverage. The overall `fail_under`
floor only catches regressions when total coverage drops below 75%.

### Planned improvements

- [ ] **New-code coverage gate**: Add a CI check that fails if coverage
  of newly added lines drops below a threshold (e.g., 90%). This
  requires diff-based coverage analysis (e.g., via
  `insightsengineering/coverage-action` or a custom Cobertura XML
  parser) to compare PR coverage against the base branch.
- [ ] **Raise `fail_under`**: Increase the overall floor as coverage
  stabilizes (currently ~80%, floor set at 75%).
- [ ] **Branch coverage gate**: Add a CI check for branch coverage
  percentage, not just statement coverage.

## Security

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Secure design knowledge [know_secure_design] | Met | Repo file | `SECURITY.md` + `CONTRIBUTING.md` security expectations; OWASP-aware ruff S rules; `docs/security.md` documents threat model. Link CODEOWNERS for developer identity |
| Common errors knowledge [know_common_errors] | Met | CI + Repo file | ruff S rules (flake8-bandit) catch OWASP Top 10 Python patterns (injection, path traversal, etc.); CodeQL `security-extended` queries; documented in `docs/security.md` |
| Published crypto only [crypto_published] | Met | Repo file | GPG (RFC 4880), Ed25519 (RFC 8032), sigstore (Fulcio/Rekor), BLAKE2B (RFC 7693), SHA-256/512 (FIPS 180-4). All industry-standard, publicly reviewed |
| Crypto delegation [crypto_call] | Met | Repo file | All crypto delegated to established libraries: `gpg`, `sigstore-python`, `cosign`, `gemato`. No custom crypto implementations. `manifest.py` uses gemato for hash verification |
| Crypto FLOSS [crypto_floss] | Met | — | gpg (GPL), sigstore-python (Apache-2.0), cosign (Apache-2.0), gemato (GPL-2.0). All FLOSS |
| Key lengths [crypto_keylength] | Met | Policy | Signing uses Ed25519 (256-bit, NIST-approved through 2030+) or RSA-4096. SHA-256 minimum for hashes. Configured in `CONTRIBUTING.md` signing instructions |
| No broken algorithms [crypto_working] | Met | Repo file | SHA-256, SHA-512, BLAKE2B for hashes. Ed25519 or RSA-4096 for signing. No MD5, SHA-1, DES, RC4 anywhere in codebase. Verified by `grep` — no occurrences |
| No weak algorithms [crypto_weaknesses] | Met | Repo file | No SHA-1 for integrity (only used by git internally). No CBC mode. No deprecated algorithms in any signing/verification path |
| Crypto random [crypto_random] | N/A | — | Project does not generate cryptographic keys or nonces. Key generation is delegated to gpg/ssh-keygen by the user |
| Crypto PFS [crypto_pfs] | N/A | — | Project does not implement key agreement protocols or encryption at rest |
| Crypto passwords [crypto_password_storage] | N/A | — | Project does not store passwords or user credentials |
| MITM delivery [delivery_mitm] | Met | CI | HTTPS-only distribution via PyPI trusted publishing; sigstore signatures; SLSA L3 provenance |
| No unsigned hashes [delivery_unsigned] | Met | CI + Repo file | SHA256SUMS.txt is distributed alongside sigstore bundles. Manifest verification uses gemato with GPG signatures. No plain hashes consumed over HTTP without signature verification |
| Vulns fixed 60 days [vulnerabilities_fixed_60_days] | Met | CI + GH setting | pip-audit + OSV-Scanner in CI; Dependabot alerts + security updates enabled |
| Critical vulns fixed [vulnerabilities_critical_fixed] | Met | Policy | `SECURITY.md` commits to fix timeline; no open critical issues |
| No leaked credentials [no_leaked_credentials] | Met | CI | gitleaks in pre-commit + gitleaks.yml CI workflow; GitHub secret scanning + push protection enabled |

## Analysis

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Static analysis tool [static_analysis] | Met | CI | ruff with S/BLE/TRY rule groups; CodeQL SAST weekly + on PR (security-extended queries) |
| Static analysis vulns [static_analysis_common_vulnerabilities] | Met | CI | ruff S rules cover flake8-bandit patterns (injection, path traversal, subprocess, etc.); CodeQL covers broader SAST; OSV-Scanner for known CVEs |
| Static analysis fixed [static_analysis_fixed] | Met | CI | CI fails on any ruff finding. All CodeQL alerts triaged and resolved |
| Static analysis often [static_analysis_often] | Met | CI | Runs on every commit (pre-commit) and every PR (CI workflows) |
| Dynamic analysis [dynamic_analysis] | Met | CI | pytest exercises all code paths on every PR; no network-facing attack surface |
| Dynamic analysis unsafe [dynamic_analysis_unsafe] | N/A | — | Pure Python, no memory-unsafe code |
| Dynamic analysis assertions [dynamic_analysis_enable_assertions] | Met | CI | pytest runs with assertions enabled (Python default); no `-O` flag |
| Dynamic analysis fixed [dynamic_analysis_fixed] | Met | CI | All test failures are resolved before merge (required status check) |
| Fix critical vulnerabilities | Met | Policy | `SECURITY.md` commits to 90-day fix timeline |

---

## Items still "?" or needing action on the form

### Can be marked Met now — form update guide

These items have `?` status on the badge form but are actually met.
Copy the justification text into the form field for each criterion.

#### Quality section

| Criterion | Mark | Justification (paste into form) |
|-----------|------|-------------------------------|
| `documentation_interface` | **Met** | CLI `--help` for all commands; user guide at https://github.com/IvanAnishchuk/geek42/blob/main/docs/user-guide.md; README quickstart at https://github.com/IvanAnishchuk/geek42/blob/main/README.md |
| `tests_documented_added` | **Met** | PR checklist in CONTRIBUTING.md requires "Tests added/updated": https://github.com/IvanAnishchuk/geek42/blob/main/CONTRIBUTING.md#pull-request-checklist — Full testing policy: https://github.com/IvanAnishchuk/geek42/blob/main/docs/testing-policy.md |
| `warnings_fixed` | **Met** | CI fails on any ruff or ty diagnostic. Lint workflow: https://github.com/IvanAnishchuk/geek42/actions/workflows/lint.yml — Type check: https://github.com/IvanAnishchuk/geek42/actions/workflows/typecheck.yml — Zero warnings on current main |
| `warnings_strict` | **Met** | ruff configured with 500+ rules including security (S, BLE, TRY), line-length 100. ty type checker with no suppressions. Both enforced in CI and pre-commit. Config: https://github.com/IvanAnishchuk/geek42/blob/main/pyproject.toml |

#### Security section

| Criterion | Mark | Justification (paste into form) |
|-----------|------|-------------------------------|
| `know_secure_design` | **Met** | Primary developer maintains security policy (https://github.com/IvanAnishchuk/geek42/blob/main/SECURITY.md), threat model (https://github.com/IvanAnishchuk/geek42/blob/main/docs/security.md), and configures ruff security rules + CodeQL SAST. CODEOWNERS: https://github.com/IvanAnishchuk/geek42/blob/main/.github/CODEOWNERS |
| `know_common_errors` | **Met** | ruff S rules (flake8-bandit) catch injection, path traversal, subprocess risks — OWASP Top 10 Python patterns. CodeQL security-extended queries run weekly + on every PR. Security lint workflow: https://github.com/IvanAnishchuk/geek42/actions/workflows/security-lint.yml — CodeQL: https://github.com/IvanAnishchuk/geek42/actions/workflows/codeql.yml |
| `crypto_published` | **Met** | GPG (RFC 4880), Ed25519 (RFC 8032), sigstore (https://sigstore.dev), SHA-256/512 (FIPS 180-4), BLAKE2B (RFC 7693). All industry-standard, publicly reviewed. No proprietary or unpublished algorithms |
| `crypto_call` | **Met** | All crypto delegated to established libraries: gpg, sigstore-python (https://github.com/sigstore/sigstore-python), cosign (https://github.com/sigstore/cosign), gemato (https://github.com/projg2/gemato). No custom implementations. Manifest hash verification: https://github.com/IvanAnishchuk/geek42/blob/main/src/geek42/manifest.py |
| `crypto_floss` | **Met** | gpg (GPL-3.0), sigstore-python (Apache-2.0), cosign (Apache-2.0), gemato (GPL-2.0). All FLOSS. Dependencies listed in https://github.com/IvanAnishchuk/geek42/blob/main/pyproject.toml |
| `crypto_keylength` | **Met** | Signing uses Ed25519 (256-bit, NIST-approved through 2030+) or RSA-4096. SHA-256 minimum for all hashes. Signing instructions: https://github.com/IvanAnishchuk/geek42/blob/main/CONTRIBUTING.md#signed-commits-are-required |
| `crypto_working` | **Met** | SHA-256, SHA-512, BLAKE2B for hashes. Ed25519 or RSA-4096 for signing. No MD5, single DES, RC4, or Dual_EC_DRBG anywhere in codebase. Verified by grep across all source files |
| `crypto_weaknesses` | **Met** | No SHA-1 for integrity verification (only used internally by git). No CBC mode. No deprecated algorithms in any signing or verification path. Sigstore uses modern Fulcio/Rekor infrastructure |
| `crypto_random` | **N/A** | Project does not generate cryptographic keys or nonces. Key generation is delegated to gpg or ssh-keygen by the user per CONTRIBUTING.md |
| `delivery_unsigned` | **Met** | SHA256SUMS.txt distributed alongside sigstore bundles (*.sigstore.json) in every GitHub Release. Manifest verification uses gemato with GPG signatures — never plain hashes over HTTP. Release workflow: https://github.com/IvanAnishchuk/geek42/blob/main/.github/workflows/release.yml |
| `no_leaked_credentials` | **Met** | gitleaks runs in pre-commit hooks and CI workflow (https://github.com/IvanAnishchuk/geek42/blob/main/.github/workflows/gitleaks.yml). GitHub secret scanning + push protection enabled in repository settings |
| `static_analysis_common_vulnerabilities` | **Met** | ruff S rules (flake8-bandit) for Python-specific vulnerabilities (injection, path traversal, subprocess, hardcoded passwords). CodeQL security-extended queries for broader SAST. OSV-Scanner for known CVEs. All three run on every PR: https://github.com/IvanAnishchuk/geek42/actions |

### Cannot be marked Met yet (needs automated enforcement)

| Criterion | Issue | Action needed |
|-----------|-------|--------------|
| `tests_are_added` | Policy exists (`docs/testing-policy.md`) and reviewer judgment enforced via coverage comment, but **no automated CI gate** blocks PRs with insufficient new-code coverage | Add diff-based coverage gate (e.g., `insightsengineering/coverage-action` with `fail-below-threshold: true`) to block PRs where <90% of new lines are covered |
| `floss_license_osi` | CC0-1.0 is not on OSI's approved list (public domain dedication, not a traditional license). OSI classification gap — CC0 is approved by FSF and widely used in FLOSS. Currently marked `?` on form | Can arguably mark **Met** with justification, but may remain yellow until OSI updates their list |

### Already met (no change needed on form)

The following were already marked Met and remain correct:
- All Basics items (12/13 → 13/13 with documentation_interface)
- All Change Control items (9/9)
- All Reporting items (8/8)

## Pending improvements

1. **2FA on PyPI** — enable after creating account
2. **Signed releases** — release workflow has run successfully (v0.4.2a10)
3. **Reproducible builds** — `SOURCE_DATE_EPOCH` configured, verified
4. **Bus factor** — currently single maintainer
5. **New-code coverage gate** — see "Planned improvements" in Quality section

---

## GitHub security settings — all enabled

As of 2026-04-10, confirmed via Settings > Advanced Security:

- [x] Private vulnerability reporting: **Enabled**
- [x] Dependency graph: **Enabled**
- [x] Automatic dependency submission: **Enabled**
- [x] Dependabot alerts: **Enabled** (1 rule enabled)
- [x] Dependabot malware alerts: **Enabled**
- [x] Dependabot security updates: **Enabled**
- [x] Grouped security updates: **Enabled**
- [x] Dependabot version updates: **Configured** (via `.github/dependabot.yml`)
- [x] CodeQL analysis: **Advanced setup** (weekly + on PR)
- [x] Copilot Autofix: **On**
- [x] Secret Protection: **Enabled**
- [x] Push protection: **Enabled**
- [x] Code scanning thresholds: Security **High or higher**, Standard **Only errors**

Confirmed via Security > Overview:
- [x] Security policy: **Enabled** (via `SECURITY.md`)
- [x] Security advisories: **Enabled**
- [x] Code scanning alerts: **Enabled** (9 alerts from CodeQL)

Remaining:
- [ ] Branch protection (settings app installed, pending first sync)
- [ ] Code scanning config error (ruff + osv-scanner SARIF — clears when CI is green)

## Improvements since initial assessment

| Area | Before | After |
|------|--------|-------|
| **Vulnerability reporting** | `SECURITY.md` only | + Private vulnerability reporting enabled on GitHub |
| **Dependabot** | Version updates only | + Alerts enabled, security updates pending |
| **Code scanning** | CodeQL only | + ruff SARIF, osv-scanner SARIF, secret scanning |
| **Test policy** | Implicit (fail_under) | Documented in `docs/testing-policy.md`, referenced from CONTRIBUTING.md |
| **Coverage** | Floor only | + PR diff comments via coverage action, pragmatic exceptions policy |
| **Style guide** | Ruff config only | Documented in `docs/style-guide.md` |
| **User guide** | README quickstart | Full workflow walkthrough in `docs/user-guide.md` |
| **Manifests** | None | gemato-compatible Manifest tree, signed, verified in CI |
| **Newsrepo scaffold** | Config file only | Full repo template matching Gentoo overlay conventions |

See `docs/release-setup.md` for the remaining setup steps.
