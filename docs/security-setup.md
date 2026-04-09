# Security Setup

This document describes how to complete the repository's supply-chain
security posture. Some settings **can be managed from files** in this
repo (committed and version-controlled); others **must be configured
manually** via the GitHub UI or API because no file-based mechanism
exists yet.

Complete all sections before the first public release.

---

## What is settable from repo files

| Setting | File | Automation |
|---------|------|------------|
| Dependabot version updates | `.github/dependabot.yml` | Native GitHub |
| Workflow permissions (per-job) | `.github/workflows/*.yml` | Native GitHub |
| Code owners | `.github/CODEOWNERS` | Native GitHub |
| Branch protection rules | `.github/settings.yml` | [repository-settings/app](https://probot.github.io/apps/settings/) |
| Repository metadata (description, topics) | `.github/settings.yml` | repository-settings/app |
| Labels | `.github/settings.yml` | repository-settings/app |
| Deploy environments | `.github/settings.yml` | repository-settings/app |
| Secret scanning | `.github/settings.yml` | repository-settings/app |
| Security policy | `SECURITY.md` | Native GitHub |
| Issue/PR templates | `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md` | Native GitHub |
| Funding | `.github/FUNDING.yml` | Native GitHub |
| Gitleaks config | `.gitleaks.toml` | Native (via workflow) |
| Pre-commit hooks | `.pre-commit-config.yaml` | Native (via workflow) |

**Setup**: install the [Settings GitHub App](https://github.com/apps/settings)
on this repository once. After that, `.github/settings.yml` becomes
the source of truth for everything listed above — any change merged
to `main` is applied automatically. This replaces most of the manual
UI clicks below.

## What still requires manual setup

Even with the Settings app installed, a few things must be done by
hand (or via the REST API with a PAT):

- **PyPI trusted publisher registration** — must be done on pypi.org
- **2FA enforcement at the org level** — org settings only
- **GHAS license activation** (for private repos) — billing settings
- **First-time enablement of secret scanning / push protection** on
  free public repos — may need a one-time UI click
- **OpenSSF Best Practices badge enrollment** — self-assessment on
  bestpractices.dev
- **GitHub Personal Access Token rotation for Dependabot** — if used

The sections below describe the manual steps in detail. If you
install the Settings app, steps 1 through 4 are handled automatically
by `.github/settings.yml` and you can skip directly to step 5.

---

## 1. Branch protection on `main`

Navigate to: **Settings → Branches → Add branch protection rule**

Pattern: `main`

Enable:

- [x] **Require a pull request before merging**
  - [x] Require approvals: 1 minimum
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners
  - [x] Require approval of the most recent reviewable push
- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Required status checks:
    - `pre-commit`
    - `Lint & format`
    - `Type check`
    - `Dependency audit`
    - `Test (Python 3.13)`
    - `CodeQL (python)`
    - `Secret scan`
    - `Review dependency changes`
- [x] **Require conversation resolution before merging**
- [x] **Require signed commits**
- [x] **Require linear history**
- [x] **Do not allow bypassing the above settings**
- [x] **Restrict who can push to matching branches** (optional, for higher tiers)
- [x] **Include administrators**

Do NOT allow:

- [ ] Allow force pushes
- [ ] Allow deletions

---

## 2. Repository security features

Navigate to: **Settings → Code security and analysis**

Enable all of the following:

| Feature | Action |
|---------|--------|
| Private vulnerability reporting | Enable |
| Dependency graph | Enable |
| Dependabot alerts | Enable |
| Dependabot security updates | Enable |
| Dependabot version updates | Enable (uses `.github/dependabot.yml`) |
| Grouped security updates | Enable |
| Code scanning | Enable (CodeQL default setup — our workflow provides custom) |
| Secret scanning | Enable |
| Secret scanning push protection | Enable |
| Secret scanning validity checks | Enable |

---

## 3. Actions settings

Navigate to: **Settings → Actions → General**

**Actions permissions:**

- Allow OWNER, and select non-OWNER actions and reusable workflows
- Allow actions created by GitHub
- Allow actions by Marketplace verified creators
- Explicitly allowlist third-party actions by full path (astral-sh/*, step-security/*, ossf/*, gitleaks/*, sigstore/*, slsa-framework/*, pypa/*, softprops/*)

**Workflow permissions:**

- Read repository contents and packages permissions (default)
- **Do not** select "Read and write" at the global level — each workflow grants its own via `permissions:`
- [x] Require approval for all outside collaborators
- [x] Require approval for first-time contributors

**Fork pull request workflows from outside collaborators:**

- Require approval for all outside collaborators (prevents secret leakage via PR workflows)

---

## 4. Environments (for release protection)

Navigate to: **Settings → Environments → New environment**

Create environment named `pypi`:

- **Required reviewers**: add repo owner (manual approval gate for each release)
- **Wait timer**: 0 minutes
- **Deployment branches**: Selected branches → `main` and tags matching `v*.*.*`

This ensures the release workflow cannot publish to PyPI without explicit
human approval, even if credentials are compromised.

---

## 5. PyPI trusted publisher setup

Before the first release, register geek42 on PyPI with trusted publishing.

### First-time (pending publisher)

1. Log in to <https://pypi.org/> with 2FA enabled
2. Navigate to **Your account → Publishing**
3. Under "Add a new pending publisher", fill in:
   - **Project name**: `geek42`
   - **Owner**: `OWNER` (your GitHub org or user)
   - **Repository name**: `geek42`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click "Add"

### After first release

Once the first release publishes successfully, the pending publisher is
converted to a real publisher automatically. No secrets or tokens are
ever needed in GitHub Actions — OIDC handles everything.

### TestPyPI (for dry runs)

Repeat the same steps on <https://test.pypi.org/> to enable dry-run
releases. The release workflow can be extended with a `workflow_dispatch`
input to target TestPyPI for pre-release testing.

---

## 6. OpenSSF Best Practices badge

Register the project at <https://www.bestpractices.dev/>:

1. Sign in with GitHub
2. "Add new project"
3. Repository URL: `https://github.com/OWNER/geek42`
4. Complete the self-assessment questionnaire (aim for "passing" on
   first submission, then work up to "silver" and "gold")
5. Copy the badge project ID into the `README.md` badges block
   (replace `XXXX` with the real ID)

---

## 7. OpenSSF Scorecard

Once the scorecard workflow runs for the first time (after merge to
main), your score appears at:

<https://scorecard.dev/viewer/?uri=github.com/OWNER/geek42>

Iterate on any failing checks. Target score: ≥ 7.0.

---

## 8. Two-factor authentication

**Every maintainer** must enable 2FA:

- GitHub: Settings → Password and authentication → Two-factor authentication
- PyPI: Account settings → Two factor authentication

For GitHub, prefer **WebAuthn / passkey** over TOTP.

Enforce 2FA organization-wide: **Organization settings → Authentication
security → Require two-factor authentication**.

---

## 9. Signed commits (GPG/SSH/sigstore)

Once `Require signed commits` is on, contributors must sign all commits.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup instructions covering
GPG, SSH signing, and sigstore `gitsign`.

---

## 10. Verification checklist (post-setup)

Before declaring the security setup complete, verify:

- [ ] A test PR from a fork is blocked by dependency-review
- [ ] An unsigned commit is rejected by branch protection
- [ ] Push protection blocks a test secret (try committing a fake AWS key — gitleaks runs locally via `pre-commit` or `gitleaks protect`)
- [ ] `pip-audit` passes in CI
- [ ] CodeQL produces zero high-severity findings
- [ ] Scorecard reports ≥ 7/10
- [ ] Dependabot opens at least one dependency update PR
- [ ] A test tag triggers the release workflow (dry run to TestPyPI)
- [ ] `gh attestation verify` succeeds on a released wheel
- [ ] `sigstore verify` succeeds on a released wheel
- [ ] `slsa-verifier verify-artifact` succeeds on a released wheel

---

## 11. Ongoing maintenance

- **Weekly**: review Dependabot PRs, merge after CI green
- **Weekly**: check Scorecard score and address regressions
- **Monthly**: review CodeQL alerts in the Security tab
- **Quarterly**: rotate any non-OIDC credentials (there should be none)
- **Per incident**: update SECURITY.md supported versions, file a GitHub Security Advisory
