# OpenSSF Best Practices Badge — Roadmap to Silver and Gold

Current status: **Passing level at 99%** (as of 2026-04-20).
Badge: <https://www.bestpractices.dev/projects/12450>

This document tracks what's needed for Silver and Gold levels.

---

## Silver level — current score: 1/17 Basics, 0/1 Change Control, 1/3 Reporting, 2/19 Quality, 1/13 Security, 2/2 Analysis

### Prerequisites

| Criterion | Status | Action |
|-----------|--------|--------|
| `achieve_passing` | **Unmet** | Finish passing level first (99% → 100%). One remaining item: `tests_are_added` needs automated new-code coverage gate |

### Basics (1/17)

| Criterion | Status | Difficulty | Action |
|-----------|--------|------------|--------|
| `dco` | ? | Easy | Already have DCO in CONTRIBUTING.md (`git commit -s`). Mark Met, link https://github.com/IvanAnishchuk/geek42/blob/main/CONTRIBUTING.md#developer-certificate-of-origin-dco |
| `governance` | ? | Easy | Write a short GOVERNANCE.md: "Single-maintainer BDFL model. @IvanAnishchuk makes all final decisions. Contributions via PRs." |
| `code_of_conduct` | ? | Easy | Adopt Contributor Covenant. Create CODE_OF_CONDUCT.md |
| `roles_responsibilities` | ? | Easy | Document in GOVERNANCE.md: maintainer role, contributor expectations |
| `access_continuity` | ? | Medium | Document bus-factor plan: second maintainer with write access, or documented key escrow process |
| `bus_factor` | ? | **Hard** | SHOULD have bus factor >= 2. Currently 1. Need a second active contributor or documented continuity plan |
| `documentation_roadmap` | ? | Easy | Write ROADMAP.md with next-year goals |
| `documentation_architecture` | ? | Medium | Write docs/architecture.md describing src layout, module relationships, data flow |
| `documentation_security` | ? | Easy | Already have docs/security.md. Mark Met, link it |
| `documentation_quick_start` | ? | Easy | Already have README.md quickstart. Mark Met |
| `documentation_current` | ? | Easy | Docs are current. Mark Met |
| `documentation_achievements` | ? | Easy | README already has OpenSSF badge. Mark Met |
| `accessibility_best_practices` | ? | Easy | CLI tool — text-only, inherently accessible. Mark Met or N/A |
| `internationalization` | ? | Easy | CLI outputs English text. GLEP 42 supports language codes. Mark Met with justification |
| `sites_password_security` | ? | Easy | No passwords stored. Mark N/A (GitHub handles auth) |
| `maintenance_or_update` | ? | Easy | Pre-1.0 software with upgrade path via pip/uv. Mark Met |

**Easy wins (can mark Met now):** `dco`, `documentation_security`, `documentation_quick_start`, `documentation_current`, `documentation_achievements`, `accessibility_best_practices`, `internationalization`, `sites_password_security`, `maintenance_or_update`

**Need new files:** `governance` → GOVERNANCE.md, `code_of_conduct` → CODE_OF_CONDUCT.md, `roles_responsibilities` → in GOVERNANCE.md, `documentation_roadmap` → ROADMAP.md, `documentation_architecture` → docs/architecture.md

**Hard:** `bus_factor` and `access_continuity` — require a second contributor or documented continuity plan

### Change Control (0/1)

| Criterion | Status | Action |
|-----------|--------|--------|
| `maintenance_or_update` | ? | Already covered in Basics above |

### Reporting (1/3)

| Criterion | Status | Action |
|-----------|--------|--------|
| `report_tracker` | Met | Already done |
| `vulnerability_report_credit` | ? | Mark N/A — no vulnerability reports received yet. Or write policy in SECURITY.md promising credit |
| `vulnerability_response_process` | ? | Already documented in SECURITY.md. Mark Met, link https://github.com/IvanAnishchuk/geek42/blob/main/SECURITY.md |

### Quality (2/19)

| Criterion | Status | Difficulty | Action |
|-----------|--------|------------|--------|
| `coding_standards` | ? | Easy | docs/style-guide.md exists. Mark Met, link it |
| `coding_standards_enforced` | ? | Easy | ruff + ty enforced in CI + pre-commit. Mark Met |
| `build_standard_variables` | ? | Easy | Pure Python, no native binaries. Mark N/A |
| `build_preserve_debug` | ? | Easy | Python — no compilation. Mark N/A |
| `build_non_recursive` | ? | Easy | hatchling handles this. Mark N/A or Met |
| `build_repeatable` | ? | Medium | SOURCE_DATE_EPOCH + PYTHONHASHSEED=0 configured in release.yml. Need to verify reproducibility |
| `installation_common` | ? | Easy | `pip install geek42` / `uv add geek42`. Mark Met |
| `installation_standard_variables` | ? | Easy | Standard pip/uv installation. Mark N/A (no DESTDIR needed) |
| `installation_development_quick` | ? | Easy | `uv sync --frozen --dev` documented in CONTRIBUTING.md. Mark Met |
| `external_dependencies` | ? | Easy | pyproject.toml lists all deps. Mark Met |
| `dependency_monitoring` | ? | Easy | Dependabot + pip-audit + OSV-Scanner in CI. Mark Met |
| `updateable_reused_components` | ? | Easy | All deps from PyPI, updated via Dependabot. Mark Met |
| `interfaces_current` | ? | Easy | Using current Python 3.13, modern libs. Mark Met |
| `automated_integration_testing` | ? | Easy | pytest runs on every push. Mark Met |
| `regression_tests_added50` | ? | Medium | Need to verify: do 50%+ of bug fixes have regression tests? Check git history |
| `test_statement_coverage80` | ? | **Medium** | Need 80% statement coverage. Currently ~80% overall but `fail_under` is 75%. Raise floor to 80 |
| `test_branch_coverage80` | ? | **Hard** | Need 80% branch coverage. Currently ~68%. Need significant test improvements |
| `test_policy_mandated` | ? | Easy | docs/testing-policy.md. Mark Met |

**Easy wins:** `coding_standards`, `coding_standards_enforced`, `build_*` (N/A), `installation_*`, `external_dependencies`, `dependency_monitoring`, `updateable_reused_components`, `interfaces_current`, `automated_integration_testing`, `test_policy_mandated`

**Medium:** `build_repeatable` (verify), `regression_tests_added50` (audit git history), `test_statement_coverage80` (raise floor)

**Hard:** `test_branch_coverage80` — need to reach 80% branch coverage project-wide. Currently ~68%. Major test gap is in `cli.py` (54% coverage)

### Security (1/13)

| Criterion | Status | Difficulty | Action |
|-----------|--------|------------|--------|
| `implement_secure_design` | ? | Easy | Documented in docs/security.md. Mark Met |
| `crypto_weaknesses` | Met | — | Already done |
| `crypto_algorithm_agility` | ? | Medium | Sigstore supports algorithm rotation. GPG supports multiple algorithms. Mark Met with justification |
| `crypto_credential_agility` | ? | Easy | N/A — project doesn't manage credentials |
| `crypto_used_network` | ? | Easy | httpx uses HTTPS only (enforced by ALLOWED_HOSTS). Mark Met or N/A |
| `crypto_tls12` | ? | Easy | httpx defaults to TLS 1.2+. Mark Met |
| `crypto_certificate_verification` | ? | Easy | httpx verifies TLS certificates by default. Mark Met |
| `crypto_verification_private` | ? | Easy | httpx verifies before sending any request. Mark Met |
| `signed_releases` | ? | Easy | Sigstore signing in release.yml. Mark Met, link release workflow |
| `version_tags_signed` | ? | Easy | `git tag -s` required by CLAUDE.md. Mark Met |
| `hardened_site` | ? | Easy | GitHub provides CSP, HSTS, X-Content-Type-Options. Mark Met |
| `security_review` | ? | **Hard** | Need a formal security review. Could be self-review documented in docs/security.md, or external audit |
| `hardening` | ? | Medium | URL validation, path traversal protection, ALLOWED_HOSTS. Document as hardening mechanisms |
| `input_validation` | ? | Easy | URL validation, filename sanitization in pyscv. Mark Met |
| `assurance_case` | ? | **Hard** | Need a formal assurance case document — threat model + trust boundaries + design principles + countered weaknesses |

**Easy wins:** Most crypto items (N/A or Met), `signed_releases`, `version_tags_signed`, `hardened_site`, `input_validation`

**Hard:** `security_review` (need formal review), `assurance_case` (need formal document)

### Analysis (2/2)

Already complete.

---

## Gold level — current score: 0/5 Basics, 1/4 Change Control, 2/7 Quality, 0/5 Security, 2/2 Analysis

### Prerequisites

| Criterion | Action |
|-----------|--------|
| `achieve_silver` | Must complete Silver first |

### Basics (0/5)

| Criterion | Difficulty | Action |
|-----------|------------|--------|
| `bus_factor` (MUST, not SHOULD) | **Very hard** | Must have bus factor >= 2. Need a second active contributor |
| `contributors_unassociated` | **Very hard** | Need 2+ unassociated significant contributors. Hard for a solo project |
| `copyright_per_file` | Medium | Add `# SPDX-License-Identifier: CC0-1.0` to every source file |
| `license_per_file` | Medium | Same — SPDX headers in every file |

### Change Control (1/4)

| Criterion | Difficulty | Action |
|-----------|------------|--------|
| `repo_distributed` | Met | Git is distributed |
| `small_tasks` | Easy | Label issues with "good first issue" |
| `require_2FA` | Easy | Enable "Require 2FA" in GitHub org settings |
| `secure_2FA` | Easy | Use TOTP/hardware key, not SMS |
| `code_review_standards` | Medium | Document code review process in CONTRIBUTING.md |
| `two_person_review` | **Hard** | Need 50%+ of changes reviewed by someone other than author. Single maintainer problem |
| `build_reproducible` | Medium | Verify and document reproducible builds |

### Quality (2/7)

| Criterion | Difficulty | Action |
|-----------|------------|--------|
| `test_invocation` | Met | `uv run pytest` |
| `test_continuous_integration` | Met | GitHub Actions |
| `test_statement_coverage90` | **Hard** | Need 90% statement coverage (currently ~80%) |
| `test_branch_coverage80` | **Hard** | Need 80% branch coverage (currently ~68%) |

### Security (0/5)

| Criterion | Difficulty | Action |
|-----------|------------|--------|
| `crypto_used_network` | Easy | httpx uses HTTPS. Met or N/A |
| `crypto_tls12` | Easy | httpx defaults to TLS 1.2+. Met |
| `hardened_site` | Easy | GitHub provides headers. Met |
| `security_review` | **Hard** | Formal security review required |
| `hardening` | Medium | Document hardening mechanisms |

### Analysis (2/2)

Already complete.

---

## Priority roadmap

### Phase 1: Reach Passing 100% (immediate)

- [ ] Add automated new-code coverage gate to CI (`tests_are_added`)

### Phase 2: Silver low-hanging fruit

- [ ] Create GOVERNANCE.md (governance, roles_responsibilities)
- [ ] Create CODE_OF_CONDUCT.md (Contributor Covenant)
- [ ] Create ROADMAP.md
- [ ] Create docs/architecture.md
- [ ] Add SPDX headers to source files (for Gold prep)
- [ ] Mark all the "easy wins" on the form (see tables above)
- [ ] Raise `fail_under` to 80 in pyproject.toml
- [ ] Add "good first issue" labels to suitable issues

### Phase 3: Silver hard items

- [ ] Reach 80% branch coverage project-wide (currently ~68%, main gap: cli.py)
- [ ] Write formal assurance case (docs/assurance-case.md)
- [ ] Verify reproducible builds
- [ ] Document vulnerability report credit policy in SECURITY.md
- [ ] Address `bus_factor` — find a second contributor or document continuity plan

### Phase 4: Gold (long-term)

- [ ] Reach 90% statement coverage
- [ ] Ensure 80% branch coverage maintained
- [ ] Get second unassociated contributor (hardest requirement)
- [ ] Enable 2FA requirement for org
- [ ] Establish two-person review process
- [ ] Conduct formal security review
- [ ] Document code review standards

---

## Blockers for each level

| Level | Blocking item | Why it's hard |
|-------|--------------|---------------|
| **Passing** | `tests_are_added` | Need automated CI gate, not just policy |
| **Silver** | `test_branch_coverage80` | cli.py at 54%, needs ~50 new tests |
| **Silver** | `bus_factor` / `access_continuity` | Single maintainer, need documented plan |
| **Silver** | `assurance_case` | Formal security argument document |
| **Gold** | `contributors_unassociated` | Need 2 unassociated significant contributors |
| **Gold** | `two_person_review` | Need 50%+ changes reviewed by non-author |
| **Gold** | `test_statement_coverage90` | Need ~10% more coverage |
