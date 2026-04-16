# First Release Setup Checklist

Everything you need to do before tagging `v0.3.0`. Items are ordered
so each step builds on the previous one.

---

## 1. GitHub Settings — Security (manual toggles)

These are in **Settings > Code security and analysis**. The screenshot
from 2026-04-10 shows most are still **Disabled**. Turn them all on.

| Setting | Current | Action |
|---------|---------|--------|
| Private vulnerability reporting | Enabled | Done |
| Dependency graph | Enabled | Done |
| Automatic dependency submission | Enabled | Done |
| Dependabot alerts | Enabled | Done (1 rule) |
| Dependabot malware alerts | Enabled | Done |
| Dependabot security updates | Enabled | Done |
| Grouped security updates | Enabled | Done |
| Dependabot version updates | Configured | Via `.github/dependabot.yml` |
| CodeQL analysis | Advanced setup | Done (weekly + on PR) |
| Copilot Autofix | On | Done |
| Secret Protection | Enabled | Done |
| Push protection | Enabled | Done |
| Code scanning thresholds | Set | Security: High or higher, Standard: Only errors |

**Code scanning config error**: "Ruff and osv-scanner are reporting
errors" — will clear once CI goes green (the SARIF upload steps
need a successful run to register with GitHub).

## 2. Branch Protection — `main`

The [repository-settings app](https://github.com/apps/settings) is
now installed. `.github/settings.yml` declares:

- Required PR reviews (1 approval, dismiss stale, code owner review)
- Required status checks (strict): pre-commit, lint, security lint,
  type check, audit, OSV scan, test, CodeQL, secret scan,
  dependency review
- Signed commits required
- Admins may bypass branch protection (`--admin`); project policy is
  to only bypass review requirement, never CI checks
- Merge commits (no linear history requirement)
- No force pushes, no branch deletion
- Conversation resolution required

The app applies these settings on the next push to main. Verify
afterward: Settings > Branches should show the protection rule.

## 3. PyPI — Trusted Publisher (OIDC, no tokens)

1. **Create a PyPI account** at <https://pypi.org/account/register/>
2. **Enable 2FA** at <https://pypi.org/manage/account/#two-factor>
   (required for trusted publishing)
3. **Add a pending trusted publisher** at
   <https://pypi.org/manage/account/publishing/>:
   - Owner: `IvanAnishchuk`
   - Repository: `geek42`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
4. The first publish will auto-create the `geek42` project on PyPI

Optional — TestPyPI first:
1. Same steps at <https://test.pypi.org/manage/account/publishing/>
2. Trigger the release workflow with `workflow_dispatch` and the
   TestPyPI option

## 4. GitHub Environment — `pypi`

1. Go to **Settings > Environments** on the repo
2. Create environment **`pypi`**
3. Check **Required reviewers** and add yourself
4. Under **Deployment branches**, select **Protected branches only**

(`.github/settings.yml` also declares `pypi` and `testpypi`
environments, but reviewer gates need manual setup.)

## 5. GitHub Pages

1. **Settings > Pages**
2. Source: **GitHub Actions** (not "Deploy from a branch")

## 6. OpenSSF Best Practices — Project 12450

Badge form: <https://www.bestpractices.dev/projects/12450/edit>

See `docs/openssf-best-practices.md` for answers to each question.
Many items are satisfied by GitHub defaults + our repo configuration:

| OpenSSF question | How it's met |
|------------------|-------------|
| Public VCS | GitHub public repo (default) |
| Issue tracker | GitHub Issues (default, `has_issues: true` in settings.yml) |
| License in standard location | `LICENSE.md` at root |
| Security policy | `SECURITY.md` at root (GitHub auto-detects) |
| Bug report process | `.github/ISSUE_TEMPLATE/config.yml` |
| Vulnerability reporting | `SECURITY.md` + private vuln reporting (enable above) |
| Contribution guide | `CONTRIBUTING.md` (GitHub auto-detects) |
| Unique versions | SemVer in `pyproject.toml` + `__version__` |
| Release notes | `CHANGELOG.md` + GitHub Releases |
| Static analysis | ruff (S/BLE/TRY rules) + CodeQL in CI |
| Signed commits | Required via branch protection |
| Automated tests | 158 pytest tests, `fail_under = 80` |
| Dependency monitoring | Dependabot alerts + `pip-audit` in CI |
| Secure delivery | PyPI OIDC + sigstore + SLSA L3 provenance |

## 7. Coverage Badge

After the first successful CI run with the coverage comment action:

1. An orphan branch `python-coverage-comment-action-data` is created
2. Uncomment the Coverage badge in `README.md`

## 8. First Release

```sh
# Make sure CI is green
gh run list --repo IvanAnishchuk/geek42 --workflow ci.yml --limit 1

# Tag
git tag -s v0.3.0 -m "v0.3.0"
git push origin v0.3.0

# The release workflow will:
#   1. Build wheel + sdist (reproducible via SOURCE_DATE_EPOCH)
#   2. Generate CycloneDX SBOM
#   3. Sign with sigstore
#   4. Create GitHub Release with artifacts
#   5. Publish to PyPI via OIDC
```

After the release succeeds, uncomment the PyPI badges in `README.md`.

---

## Security TODO

### Before v0.3.0 (manual GitHub UI actions)

- [x] Enable private vulnerability reporting
- [x] Enable dependency graph
- [x] Enable Dependabot alerts
- [x] Enable Dependabot malware alerts
- [x] Enable Dependabot security updates
- [x] Enable grouped security updates
- [x] Enable secret scanning
- [x] Enable push protection
- [x] Install repository-settings app
- [ ] Verify branch protection applied by settings app
- [ ] Enable 2FA on PyPI account
- [ ] Create `pypi` environment with reviewer gate
- [ ] Enable GitHub Pages (source: GitHub Actions)
- [ ] Complete OpenSSF Best Practices form (project 12450)
- [ ] Fix CI (coverage comment action) so all checks go green

### After first release

- [ ] Verify sigstore signatures on the published wheel
- [ ] Verify SLSA provenance on the GitHub Release
- [ ] Verify reproducible build (two builds with same
      `SOURCE_DATE_EPOCH` produce identical artifacts)
- [ ] Uncomment PyPI + Coverage badges in README
- [ ] Run `pip-audit` against the published package
- [ ] Review Scorecard results and address any findings
- [ ] Confirm code scanning errors cleared (ruff + osv-scanner SARIF)

### Ongoing

- [ ] Respond to Dependabot PRs within 7 days
- [ ] Respond to vulnerability reports per `SECURITY.md` SLA
- [ ] Keep `pip-audit` passing in CI (zero known vulns)
- [ ] Re-run OpenSSF Best Practices self-assessment annually
- [ ] Review and rotate any API tokens (ideally: none, OIDC only)
- [ ] Consider adding a second maintainer (bus factor)

### What's already automated (no action needed)

- Conventional Commits enforced by `conventional-pre-commit` hook
- Branch protection declared in `.github/settings.yml`
- Required status checks declared in `.github/settings.yml`
- CODEOWNERS for security-sensitive paths
- CodeQL weekly + on PR
- Gitleaks secret scanning on push
- Dependency review on PRs (license + vuln gating)
- OpenSSF Scorecard weekly
- Pre-commit hooks for formatting, linting, security
