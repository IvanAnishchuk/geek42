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
| Working build system | Met | Repo file | `hatchling` via `pyproject.toml`; `uv build` produces wheel + sdist |
| Automated test suite | Met | CI | 158 pytest tests; CI runs on every push/PR (`ci.yml` test job) |
| New tests for new functionality | Met | Policy | `CONTRIBUTING.md` requires tests; `fail_under = 80` enforced; coverage >93% |
| FLOSS test framework | Met | Repo file | pytest (MIT license) |
| Test policy | Met | Repo file + CI | `pyproject.toml` `fail_under = 80`; branch protection requires test job to pass |

### Test policy detail

All new features and bug fixes **must** include tests. This is
enforced by:

1. **Coverage floor**: `[tool.coverage.report] fail_under = 80` in
   `pyproject.toml` — CI fails if coverage drops below 80%.
2. **Required status check**: `Test (Python 3.13)` is a required
   check in branch protection — PRs cannot merge without passing tests.
3. **Contributing guide**: `CONTRIBUTING.md` states that PRs must
   include tests for new functionality and regression tests for bugs.
4. **Code review**: `CODEOWNERS` requires code-owner approval; reviewers
   check for test coverage.

## Security

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Secure development knowledge | Met | Repo file | `CONTRIBUTING.md` security expectations; ruff S/BLE/TRY rules |
| Use basic good crypto | Met | CI + Repo file | BLAKE2B+SHA512 Manifests (gemato); GPG/sigstore for signing; no custom crypto |
| Secured delivery against MITM | Met | CI | PyPI OIDC trusted publishing; sigstore signatures; SLSA L3 provenance |
| Publicly known vulns fixed | Met | CI + GH setting | `pip-audit` in CI; Dependabot alerts + security updates (enable in Settings) |
| Static analysis | Met | CI | ruff (flake8-bandit S rules) + CodeQL `security-extended` (enabled, last scan confirmed) |

## Analysis

| Question | Answer | How | Detail |
|----------|--------|-----|--------|
| Static analysis tool | Met | CI | ruff with S/BLE/TRY rule groups; CodeQL SAST weekly + on PR (Advanced setup, enabled) |
| Dynamic analysis | N/A | — | CLI tool, no network-facing attack surface; pytest exercises all code paths |
| Fix critical vulnerabilities | Met | Policy | `SECURITY.md` commits to 90-day fix timeline |

---

## Items still "?" or pending first execution

1. **2FA on PyPI** — enable after creating account (before first publish)
2. **Signed releases** — release workflow configured but hasn't run yet
   (needs first `v*.*.*` tag)
3. **Reproducible builds** — `SOURCE_DATE_EPOCH` + `PYTHONHASHSEED=0`
   configured in release workflow but untested until first release
4. **Bus factor** — currently single maintainer

---

## GitHub settings required (not automatable via files)

These toggles in **Settings > Code security and analysis** don't have
file-based equivalents. They must be enabled manually:

- Private vulnerability reporting
- Dependency graph
- Dependabot alerts + malware alerts + security updates
- Secret scanning + push protection

See `docs/release-setup.md` for the full checklist with current status.
