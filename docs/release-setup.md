# First Release Setup Checklist

Everything you need to do before tagging `v0.3.0`. Items are ordered
so each step builds on the previous one.

---

## 1. PyPI — Trusted Publisher (OIDC, no tokens)

PyPI supports "trusted publishing" where GitHub Actions authenticates
via OIDC — no API tokens needed.

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

## 2. GitHub Environment — `pypi`

The release workflow deploys to a `pypi` environment with reviewer gate.

1. Go to **Settings > Environments** on the repo
2. Create environment **`pypi`**
3. Check **Required reviewers** and add yourself
4. Under **Deployment branches**, select **Protected branches only**

## 3. GitHub Pages

1. **Settings > Pages**
2. Source: **GitHub Actions** (not "Deploy from a branch")
3. The `deploy.yml` workflow (in the newsrepo template) or the
   existing CI deploy job handles the rest

## 4. GitHub Settings — Security

Do these in **Settings > Code security and analysis**:

- [x] **Dependabot alerts**: enable
- [x] **Dependabot security updates**: enable
- [x] **Dependabot version updates**: already configured via `.github/dependabot.yml`
- [x] **Secret scanning**: enable
- [x] **Push protection**: enable (blocks commits containing secrets)
- [x] **CodeQL**: already runs via `.github/workflows/codeql.yml`

## 5. Branch Protection — `main`

**Settings > Branches > Add rule** for `main`:

- [x] Require pull request before merging (1 approval)
- [x] Require status checks: `pre-commit`, `test`, `lint`, `audit`
- [x] Require signed commits
- [x] Do not allow bypassing
- [x] Restrict who can push (yourself only)

Note: `.github/settings.yml` declares these if the
[repository-settings app](https://github.com/apps/settings) is
installed.

## 6. OpenSSF Best Practices — Project 12450

Badge form: <https://www.bestpractices.dev/projects/12450/edit>

See `docs/openssf-best-practices.md` for answers to each question.
After completing PyPI setup and the first release, revisit the "?"
items (2FA, signed releases, reproducibility).

## 7. Scorecard

The OpenSSF Scorecard workflow (`.github/workflows/scorecard.yml`)
runs automatically. After the first successful run:

1. Results appear at
   <https://scorecard.dev/viewer/?uri=github.com/IvanAnishchuk/geek42>
2. SARIF results upload to **Security > Code scanning**

## 8. Coverage Badge

After the first successful CI run with the coverage comment action:

1. An orphan branch `python-coverage-comment-action-data` is created
2. Uncomment the Coverage badge in `README.md`

## 9. First Release

```sh
# Make sure CI is green
gh run list --workflow ci.yml --limit 1

# Tag
git tag -s v0.3.0 -m "v0.3.0"
git push origin v0.3.0

# The release workflow will:
#   1. Build wheel + sdist (reproducible)
#   2. Generate CycloneDX SBOM
#   3. Sign with sigstore
#   4. Create GitHub Release with artifacts
#   5. Publish to PyPI via OIDC
```

After the release succeeds, uncomment the PyPI badges in `README.md`.

---

## Security TODO

Items requiring manual action, policy decisions, or GitHub settings
that cannot be automated via repo files:

### Immediate (before v0.3.0)

- [ ] **Install [repository-settings app](https://github.com/apps/settings)**
      on the repo — this activates `.github/settings.yml` which
      declares branch protection, required status checks, signed
      commits, dismiss stale reviews, etc. Without it, the file is
      inert. Alternatively, configure manually:
      Settings > Branches > Add rule for `main`.
- [ ] **Enable branch protection on `main`** (if not using the app):
      require PR reviews (1), require status checks (pre-commit,
      test, lint, audit, CodeQL, etc.), require signed commits,
      enforce for admins, require linear history.
- [ ] Enable 2FA on PyPI account
- [ ] Create `pypi` environment with reviewer gate
- [ ] Enable secret scanning + push protection
      (Settings > Code security and analysis)
- [ ] Enable Dependabot alerts + security updates
- [ ] Review and complete OpenSSF Best Practices form

### After first release

- [ ] Verify sigstore signatures on the published wheel
- [ ] Verify SLSA provenance on the GitHub Release
- [ ] Verify reproducible build (`SOURCE_DATE_EPOCH` produces
      identical artifacts)
- [ ] Uncomment PyPI + Coverage badges in README
- [ ] Run `pip-audit` against the published package
- [ ] Review Scorecard results and address any findings

### Ongoing

- [ ] Respond to Dependabot PRs within 7 days
- [ ] Respond to vulnerability reports per `SECURITY.md` SLA
- [ ] Keep `pip-audit` passing in CI (zero known vulns)
- [ ] Re-run OpenSSF Best Practices self-assessment annually
- [ ] Review and rotate any API tokens (ideally: none, OIDC only)
- [ ] Consider adding a second maintainer (bus factor)
