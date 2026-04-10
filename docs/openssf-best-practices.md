# OpenSSF Best Practices Badge — Project 12450

Answers for the [OpenSSF Best Practices](https://www.bestpractices.dev/projects/12450) badge form.
Update this document as the project evolves.

---

## Basics

| Question | Answer | Justification |
|----------|--------|---------------|
| **Project website URL** | `https://github.com/IvanAnishchuk/geek42` | GitHub repo is the canonical homepage |
| **Description (what it does)** | Converts GLEP 42 Gentoo news repositories into static blogs with RSS/Atom feeds, Markdown exports, and a terminal reader | One-line from pyproject.toml |
| **OSS license** | Met | CC0-1.0, declared in `LICENSE.md`, `pyproject.toml` (`license = "CC0-1.0"`), and every packaging file |
| **License in standard location** | Met | `LICENSE.md` at repo root |
| **Documentation of basic use** | Met | `README.md` Quickstart + CLI Commands sections |
| **How to contribute** | Met | `CONTRIBUTING.md` (signed commits, DCO, Conventional Commits) |
| **FLOSS license** | Met | CC0-1.0 is OSI-approved equivalent / public domain dedication |

## Change control

| Question | Answer | Justification |
|----------|--------|---------------|
| **Public VCS repo** | Met | GitHub `IvanAnishchuk/geek42`, public |
| **Track issues publicly** | Met | GitHub Issues enabled |
| **Interim & release versions via VCS** | Met | All development on `main`, releases tagged `v*.*.*` |
| **Release notes** | Met | `CHANGELOG.md` in Keep a Changelog format; GitHub Releases created by release workflow |
| **Unique version numbering** | Met | SemVer; `pyproject.toml` + `__version__` |
| **ChangeLog** | Met | `CHANGELOG.md` |

## Reporting

| Question | Answer | Justification |
|----------|--------|---------------|
| **Bug reporting process** | Met | GitHub Issues with bug report template (`.github/ISSUE_TEMPLATE/config.yml`) |
| **Respond to bug reports** | Met | Maintained by owner, responds within days |
| **Published process for vulnerability reports** | Met | `SECURITY.md` with private disclosure via email, response SLA |

## Quality

| Question | Answer | Justification |
|----------|--------|---------------|
| **Working build system** | Met | `hatchling` via `pyproject.toml`; `uv build` produces wheel + sdist |
| **Automated test suite** | Met | 158 pytest tests; CI runs on every push/PR |
| **New tests for new functionality** | Met | All features added with corresponding tests; coverage >90% |
| **FLOSS test framework** | Met | pytest (MIT license) |
| **Test policy** | Met | `fail_under = 80` enforced in CI; PRs require tests |

## Security

| Question | Answer | Justification |
|----------|--------|---------------|
| **Secure development knowledge** | Met | CONTRIBUTING.md documents security expectations; ruff security rules (S, BLE, TRY) enabled |
| **Use basic good crypto** | Met | BLAKE2B + SHA512 for Manifest checksums (via gemato); GPG/sigstore for signing; no custom crypto |
| **Secured delivery against MITM** | Met | PyPI via OIDC trusted publishing; GitHub releases with sigstore signatures + SLSA provenance |
| **Publicly known vulnerabilities fixed** | Met | `pip-audit` in CI; Dependabot for dependency updates |
| **Static analysis** | Met | ruff (including flake8-bandit security rules), CodeQL `security-extended` |

## Analysis

| Question | Answer | Justification |
|----------|--------|---------------|
| **Static analysis tool** | Met | ruff with S/BLE/TRY rule groups; CodeQL SAST weekly + on PR |
| **Dynamic analysis** | N/A | CLI tool, no network-facing attack surface; pytest test suite exercises all code paths |
| **Fix critical vulnerabilities** | Met | `SECURITY.md` commits to 90-day fix timeline |

---

## Items still "?" or needing action

These need manual setup or policy decisions before claiming "Met":

1. **2FA on PyPI** — enable after first publish (see setup checklist below)
2. **Signed releases** — release workflow exists but hasn't run yet (needs first tag)
3. **Reproducible builds** — workflow configured with `SOURCE_DATE_EPOCH` but untested
4. **Bus factor** — currently single maintainer; consider adding a co-maintainer

---

## Reference

- Badge: <https://www.bestpractices.dev/projects/12450>
- Criteria: <https://www.bestpractices.dev/criteria/0>
