# Security Architecture

This document is the **technical reference** for geek42's supply-chain
security. For the disclosure policy see [SECURITY.md](../SECURITY.md);
for the repo-owner configuration checklist see
[security-setup.md](security-setup.md).

## Goals

1. **Verifiable origin** — anyone can cryptographically prove a
   published artifact was built from a specific commit in this
   repository by GitHub Actions, with no trust in the maintainers'
   credentials.
2. **Non-repudiable signatures** — every release is keylessly signed
   via [sigstore](https://sigstore.dev), with OIDC identity bound to
   the release workflow.
3. **Transitive transparency** — a CycloneDX SBOM is attached and
   attested so consumers can audit and monitor every dependency.
4. **Defense in depth** — no single compromise (stolen laptop,
   phished account, corrupted dependency, typo-squatted package)
   should be sufficient to ship a malicious release.
5. **Zero long-lived secrets** — PyPI publishing uses OIDC trusted
   publishing; no API tokens exist in GitHub Actions.

---

## Threat model

### Assets

- The published source code (`main` branch)
- Published PyPI releases (`geek42-X.Y.Z-py3-none-any.whl`, sdist)
- The CI/CD pipeline and its attestations
- Maintainer identities (GitHub, PyPI)
- Developer workstations

### Adversaries

| Adversary | Capability | Relevant defenses |
|-----------|-----------|-------------------|
| **Script kiddie** | Pull public artifacts, try old CVEs | Dependabot, CodeQL, pip-audit |
| **Opportunistic attacker** | Typosquat dependency, submit malicious PR | Dependency review, CODEOWNERS, branch protection |
| **Credential thief** | Steal maintainer PyPI token | No PyPI tokens exist (OIDC only) |
| **Account compromise** | Hijack maintainer GitHub account | 2FA, signed commits, `pypi` environment gate |
| **Insider threat** | Maintainer pushes backdoor directly | Required reviewers, CODEOWNERS, audit trail |
| **CI compromise** | Modify running workflow | SHA-pinned actions, harden-runner, minimal permissions |
| **Supply chain** | Compromise a transitive dependency | SBOM, pip-audit, hash-pinned uv.lock, CodeQL |
| **Nation-state** | Sophisticated multi-vector | Scope: partially mitigated by SLSA L3 + sigstore |

### Out of scope

- Vulnerabilities in dependencies themselves (report upstream)
- Attacks on the PyPI index server itself
- Attacks on GitHub's infrastructure itself (we rely on GitHub's own
  SOC 2, SLSA, and incident response)
- Physical attacks on GitHub-hosted runners

---

## Defense layers

### Layer 1: source integrity

- **Signed commits required** on `main` (branch protection rule)
  - GPG, SSH signing, or sigstore gitsign
  - See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup
- **Linear history** enforced — no merge commits that could obscure
  history rewrites
- **CODEOWNERS** requires maintainer approval on every PR
- **Required reviewers** — cannot merge without human review
- **No force push, no deletion** of `main`

### Layer 2: static analysis

- **Ruff** with security rule groups `S` (bandit), `BLE` (blind
  except), `TRY` (tryceratops)
- **CodeQL** with `security-extended` and `security-and-quality`
  query suites — runs on every PR and push to main, plus weekly
- **Ty** static type checker — catches entire classes of bugs at CI
  time
- **Gitleaks** — secret scanning on every push and PR

### Layer 3: dependency supply chain

- **`uv.lock`** is committed, contains sha256 hashes for every
  transitive dep
- **`uv sync --frozen`** refuses to install if lockfile is out of
  sync with `pyproject.toml` or hashes don't match
- **Dependabot** — weekly grouped PRs for minor/patch updates
- **Dependency review** (PR-time) — blocks introductions of
  moderate-severity vulns and forbidden licenses (GPL-2/3, AGPL)
- **pip-audit** — runs on every CI build against the exported
  requirements, fails on any known vuln
- **CycloneDX SBOM** — generated and attested with every release

### Layer 4: build integrity

- **Reproducible builds** — given the same source and
  `SOURCE_DATE_EPOCH`, geek42 produces byte-identical wheels. This
  allows independent verification by rebuilding from source and
  comparing SHA-256 hashes. Verified locally: two consecutive builds
  yield identical artifacts.
- **Ephemeral runners** — every build runs on a fresh GitHub-hosted
  runner; no persistent state between runs
- **SHA-pinned actions** — every `uses:` references a specific commit
  SHA, not a tag. Mitigates tag-retargeting attacks on third-party
  actions.
- **`step-security/harden-runner`** — first step in every job:
  - Monitors all network egress
  - Audits all process executions
  - In "block" mode (future), denies any unexpected egress
- **Minimal permissions** — top-level `permissions: {}` denies all
  tokens by default; each job opts in to the minimum it needs
  (usually just `contents: read`)
- **`persist-credentials: false`** on checkout — the GITHUB_TOKEN is
  not persisted in `.git/config`, preventing subsequent steps from
  abusing it

### Layer 5: release signing & attestation

Four independent pieces of cryptographic evidence are attached to
every release:

1. **Sigstore bundle** (`*.sigstore`)
   - Keyless signing via Fulcio + Rekor
   - Identity: `https://github.com/OWNER/geek42/.github/workflows/release.yml@refs/tags/vX.Y.Z`
   - Issuer: `https://token.actions.githubusercontent.com`
   - Transparency log entry at `rekor.sigstore.dev`
2. **GitHub build provenance** (in-toto attestation)
   - Generated by `actions/attest-build-provenance`
   - Verifiable via `gh attestation verify`
   - Includes: workflow path, commit SHA, runner environment
3. **SBOM attestation** (in-toto)
   - Generated by `actions/attest-sbom`
   - Binds the CycloneDX SBOM to the wheel hash
4. **SLSA Level 3 provenance** (`*.intoto.jsonl`)
   - Generated by `slsa-framework/slsa-github-generator` running in an
     isolated reusable workflow
   - **Non-falsifiable**: the builder runs in a separate job from the
     build itself, so a compromise of the `build` job cannot forge the
     provenance
   - Verifiable via `slsa-verifier`

### Layer 6: publishing

- **PyPI trusted publisher (OIDC)** — no API tokens exist. GitHub
  Actions requests a short-lived (15-min) OIDC token, PyPI verifies
  it came from our exact workflow, and issues a one-time upload
  token. A compromise of the GitHub repo does not give PyPI access
  unless the attacker can also run our release workflow.
- **`pypi` environment gate** — requires manual approval from the
  repo owner before the `publish-pypi` job can run. Even a compromised
  GitHub account cannot publish silently.
- **`environment:` deployment branches** — restricted to `main` and
  tags matching `v*.*.*`. Branch protection prevents push of
  arbitrary tags without review.

### Layer 7: runtime safety

While not strictly supply chain, the following mitigate runtime risks
for users of geek42:

- **No `shell=True`, `eval`, `exec`, `os.system`** — audited and
  enforced by ruff `S` rules
- **Absolute git path** — `shutil.which("git")` at import time
  prevents PATH hijacking
- **Subprocess arguments are always lists** — never string-joined,
  never interpolated into shell
- **XML parsing** — we *emit* XML via stdlib `xml.etree` but never
  parse untrusted XML as input
- **No network calls in parser** — news items are read from local
  git clones only
- **Editor invocation** — the only user-controlled command; the user
  authorizes it explicitly via `$EDITOR`

---

## Provenance chain

```
┌────────────────────────────────────────────────────────┐
│  1. Developer commits signed code to a feature branch │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  2. PR opened. CI runs: lint, typecheck, tests,       │
│     pip-audit, CodeQL, gitleaks, dependency-review    │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  3. CODEOWNER reviews + approves. PR merged to main.  │
│     Branch protection enforces signed commits + CI.   │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  4. Maintainer pushes signed tag v0.X.Y                │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  5. release.yml triggers:                              │
│     a. Harden runner                                   │
│     b. Checkout tag, fetch-depth 0                     │
│     c. uv build (reproducible, SOURCE_DATE_EPOCH)      │
│     d. cyclonedx-py generates SBOM                     │
│     e. actions/attest-build-provenance → in-toto       │
│     f. actions/attest-sbom → in-toto                   │
│     g. sigstore signs wheel + sdist                    │
│     h. SLSA generator produces L3 provenance           │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  6. pypi environment gate — manual approval required  │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  7. PyPI publish via OIDC trusted publishing          │
│     - 15-min GitHub OIDC token                         │
│     - PyPI verifies identity matches registered one    │
│     - Short-lived upload token issued                  │
└────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  8. GitHub Release created with all artifacts,         │
│     signatures, SBOM, and provenance attached         │
└────────────────────────────────────────────────────────┘
```

---

## Verification

As a consumer of geek42, you can independently verify any release.

### Quick verification (one command)

```sh
gh attestation verify geek42-0.2.0-py3-none-any.whl --owner OWNER
```

This checks the GitHub-hosted build provenance attestation and
confirms the wheel was built by the release workflow.

### Full verification (four independent checks)

```sh
# 0. Download everything from the GitHub release
gh release download v0.2.0 --repo OWNER/geek42
ls
# geek42-0.2.0-py3-none-any.whl
# geek42-0.2.0.tar.gz
# geek42-0.2.0-py3-none-any.whl.sigstore
# geek42-0.2.0.tar.gz.sigstore
# geek42-sbom.cdx.json
# geek42-provenance.intoto.jsonl
# SHA256SUMS.txt

# 1. Verify hashes
sha256sum -c SHA256SUMS.txt

# 2. Sigstore signature (keyless, verifies workflow identity)
uv tool run sigstore verify identity \
    --cert-identity-regexp '^https://github\.com/OWNER/geek42/\.github/workflows/release\.yml@' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    --bundle geek42-0.2.0-py3-none-any.whl.sigstore \
    geek42-0.2.0-py3-none-any.whl

# 3. GitHub build provenance attestation
gh attestation verify geek42-0.2.0-py3-none-any.whl --owner OWNER

# 4. SLSA Level 3 provenance (non-falsifiable)
slsa-verifier verify-artifact \
    --provenance-path geek42-provenance.intoto.jsonl \
    --source-uri github.com/OWNER/geek42 \
    --source-tag v0.2.0 \
    geek42-0.2.0-py3-none-any.whl

# 5. SBOM sanity check
jq '.components | length' geek42-sbom.cdx.json
```

### Reproducibility verification

To prove the wheel was built from the tagged source (and not tampered
with in the pipeline), rebuild from source and compare hashes:

```sh
git clone --branch v0.2.0 https://github.com/OWNER/geek42
cd geek42

# Use the exact SOURCE_DATE_EPOCH from the tag commit
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export PYTHONHASHSEED=0

uv build
sha256sum dist/*.whl dist/*.tar.gz
```

The SHA-256 of your local build must match the one in
`SHA256SUMS.txt` from the GitHub release.

---

## Incident response

If a security issue is discovered in a released version:

1. **Triage** (within 7 days of private report per SECURITY.md)
2. **Patch** on a private fork if the vulnerability is sensitive
3. **CVE** requested from GitHub's CNA via Security Advisory
4. **Release** a patched version with SLSA provenance unchanged
5. **Yank** the vulnerable version from PyPI (`pip install
   geek42==X.Y.Z` still works for reproducibility, but the version is
   marked yanked so `pip install geek42` skips it)
6. **Publish** the Security Advisory on GitHub, notifying all users
   via the dependency graph
7. **Post-mortem** added to `docs/incidents/YYYY-MM-DD-slug.md`

If a maintainer account is compromised:

1. Revoke all sessions and tokens immediately
2. Rotate 2FA secrets
3. Audit recent commits on `main` — branch protection should prevent
   unauthorized changes, but verify
4. Audit recent PyPI releases — since no tokens exist, an attacker
   would have had to go through the `pypi` environment gate
5. If a rogue release exists: yank it, publish an advisory, release
   a corrected patched version

If a dependency is compromised:

1. `pip-audit` should flag it within 24 hours of CVE publication
2. Dependabot opens a PR automatically
3. If exploitation is active, pin to an unaffected version and
   release a patch
4. If no fix exists upstream, consider vendoring a minimal fix or
   removing the dependency

---

## Scope limits

**geek42 does not**:

- Verify the authenticity of the git repositories that it clones
  (`geek42 pull`). Users should pin sources to HTTPS with known
  fingerprints or use SSH with host-key verification.
- Sandbox news item contents. Malicious news items can contain
  misleading content but cannot execute code (they are plain text).
- Defend against a compromised user workstation. If the attacker
  has code execution on your machine, they can modify the clone and
  bypass these guarantees.

**geek42 explicitly does**:

- Provide cryptographic proof of every byte published to PyPI
- Log every build step to an immutable transparency log (Rekor)
- Allow third-party reproduction of any release
- Minimize the blast radius of any single compromise

---

## References

- [SLSA](https://slsa.dev/) — Supply-chain Levels for Software Artifacts
- [sigstore](https://sigstore.dev/) — signing and transparency
- [CycloneDX](https://cyclonedx.org/) — SBOM standard
- [OpenSSF Scorecard](https://scorecard.dev/) — automated best-practice audit
- [OpenSSF Best Practices](https://www.bestpractices.dev/) — self-assessment badge
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) — OIDC for PyPI
- [in-toto](https://in-toto.io/) — attestation framework
- [Rekor](https://docs.sigstore.dev/rekor/overview/) — transparency log
