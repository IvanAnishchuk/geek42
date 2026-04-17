# Multi-Platform Supply-Chain Verification for pyscv

Research document covering feature parity between source code platforms
for extending `pyscv` beyond GitHub.

**Date:** 2026-04-17
**Status:** Research / RFC

---

## Table of Contents

1. [Current GitHub Dependencies](#current-github-dependencies)
2. [Platform Analysis](#platform-analysis)
   - [GitLab](#gitlab)
   - [Bitbucket](#bitbucket)
   - [Codeberg / Gitea / Forgejo](#codeberg--gitea--forgejo)
   - [SourceHut](#sourcehut)
   - [Google Cloud Build](#google-cloud-build)
3. [Cross-Cutting Concerns](#cross-cutting-concerns)
   - [PyPI Trusted Publishing](#pypi-trusted-publishing)
   - [Sigstore OIDC Issuers](#sigstore-oidc-issuers)
   - [SLSA Framework Support](#slsa-framework-support)
4. [Comparison Matrix](#comparison-matrix)
5. [Architecture Recommendations](#architecture-recommendations)
6. [Implementation Roadmap](#implementation-roadmap)
7. [References](#references)

---

## Current GitHub Dependencies

`pyscv` currently relies on these GitHub-specific features:

| Feature | GitHub Component | pyscv Usage |
|---------|-----------------|-------------|
| Release assets API | `api.github.com/repos/{slug}/releases/tags/{tag}` | Download `.whl`, `.tar.gz` |
| CI/CD OIDC | `token.actions.githubusercontent.com` | Identity verification |
| Sigstore signing | GitHub Actions + cosign/sigstore | Artifact signing |
| SLSA L3 provenance | `slsa-framework/slsa-github-generator`, `actions/attest` | Provenance generation |
| PEP 740 attestations | Trusted publishing via GitHub Actions OIDC | PyPI attestations |
| Attestations API | `gh attestation verify` | Verification |
| Artifact hosting | `objects.githubusercontent.com`, `release-assets.githubusercontent.com` | Download URLs |

---

## Platform Analysis

### GitLab

**Overall: Strongest alternative. Most features available or achievable.**

#### Release Assets API

GitLab has a Releases API with direct asset download:

```
GET /api/v4/projects/:id/releases/:tag_name
GET /api/v4/projects/:id/releases/:tag_name/assets/links
```

Release assets can be:
- **Links** — external URLs attached to a release
- **Sources** — auto-generated source archives
- **Package Registry files** — linked from GitLab's built-in package registry

Direct download URLs follow the pattern:
```
https://gitlab.com/{group}/{project}/-/releases/{tag}/downloads/{filename}
```

For the Generic Package Registry:
```
https://gitlab.com/api/v4/projects/:id/packages/generic/:name/:version/:filename
```

**Key differences from GitHub:**
- Project identifier is numeric ID or URL-encoded path (`group%2Fproject`)
- Release links are separate from release metadata (two API calls)
- Generic Package Registry is often used instead of release assets
- Rate limits: 2000 req/min authenticated, 500 req/min unauthenticated (vs GitHub's 5000/hr authenticated, 60/hr unauthenticated)

**Refs:**
- https://docs.gitlab.com/ee/api/releases/
- https://docs.gitlab.com/ee/api/releases/links.html
- https://docs.gitlab.com/ee/user/packages/generic_packages/

#### CI/CD OIDC

GitLab CI/CD supports OIDC token generation since GitLab 15.7:

```yaml
job:
  id_tokens:
    SIGSTORE_ID_TOKEN:
      aud: sigstore
```

OIDC issuer: `https://gitlab.com` (or self-hosted instance URL)

The token includes claims like:
- `project_path` — e.g., `group/project`
- `pipeline_source` — how the pipeline was triggered
- `ref` — branch/tag ref
- `environment` — deployment environment (if applicable)

**Key differences:**
- Issuer URL is the GitLab instance itself, not a separate token service
- Self-hosted GitLab instances have their own issuer URL — pyscv must support configurable issuers
- Token claims use different field names than GitHub (`project_path` vs `repository`)

**Refs:**
- https://docs.gitlab.com/ee/ci/secrets/id_token_authentication.html
- https://docs.gitlab.com/ee/ci/cloud_services/

#### Sigstore Integration

Sigstore's Fulcio CA accepts GitLab OIDC tokens. The `sigstore-python` and
`cosign` tools work with GitLab CI OIDC out of the box.

GitLab published a guide for sigstore container signing in CI:

```yaml
sign:
  image: gcr.io/sigstore-staging/cosign
  id_tokens:
    SIGSTORE_ID_TOKEN:
      aud: sigstore
  script:
    - cosign sign --identity-token=$SIGSTORE_ID_TOKEN $IMAGE
```

For Python artifacts, `sigstore-python` can be used similarly.

**Refs:**
- https://docs.gitlab.com/ee/ci/yaml/signing_examples.html
- https://docs.sigstore.dev/certificate_authority/oidc-in-fulcio/

#### SLSA Provenance

**No native SLSA L3 generator for GitLab.** This is the biggest gap.

- The `slsa-framework/slsa-github-generator` is GitHub-specific
- There is a community `slsa-framework/slsa-verifier` that can verify
  provenance from multiple builders, but generation is limited
- Google Cloud Build can generate SLSA L3 provenance and can be triggered
  from GitLab CI, but this adds infrastructure complexity
- GitLab has discussed native SLSA support but no production implementation
  as of early 2026

**Workaround:** Use `in-toto` directly to generate provenance statements
in GitLab CI, signed with sigstore. This gives SLSA L1-L2 but not L3
(which requires a hardened, isolated build service).

**Refs:**
- https://github.com/slsa-framework/slsa-github-generator (GitHub-only)
- https://slsa.dev/spec/v1.0/levels
- https://gitlab.com/groups/gitlab-org/-/epics/9253 (GitLab SLSA tracking epic)

#### PyPI Trusted Publishing

**Supported since mid-2024.** GitLab CI can publish to PyPI with OIDC-based
trusted publishing, including PEP 740 attestations.

Configuration on PyPI:
- Project URL: `https://gitlab.com/{namespace}/{project}`
- CI config file path: e.g., `.gitlab-ci.yml`
- Environment: the GitLab environment name

**Refs:**
- https://docs.pypi.org/trusted-publishers/adding-a-publisher/
- https://blog.pypi.org/posts/2024-03-29-gitlab-trusted-publishers/

---

### Bitbucket

**Overall: Very limited. Not a viable target for full SCV.**

#### Release Assets API

Bitbucket has a **Downloads API** (not releases):

```
GET /2.0/repositories/{workspace}/{repo_slug}/downloads
POST /2.0/repositories/{workspace}/{repo_slug}/downloads
```

Files are uploaded to the Downloads section, not tied to tags/releases.
There is no concept of "release assets" linked to a git tag.

**Key limitations:**
- No tag-based release model
- Downloads are a flat list, not versioned
- No API to list downloads filtered by version
- Would need a naming convention to associate files with versions

#### CI/CD OIDC

Bitbucket Pipelines supports OIDC for **cloud provider authentication only**
(AWS, GCP, Azure). The OIDC tokens are **not accepted by Fulcio or PyPI**.

The issuer is `https://api.bitbucket.org/2.0/workspaces/{workspace}/pipelines-config/identity/oidc`
and is not in Fulcio's accepted issuer list.

**Refs:**
- https://support.atlassian.com/bitbucket-cloud/docs/deploy-on-aws-using-bitbucket-pipelines-openid-connect/

#### Sigstore / SLSA / Attestations

- **No sigstore integration** — OIDC tokens not accepted by Fulcio
- **No SLSA provenance generation**
- **No PyPI trusted publishing** — not in PyPI's trusted publisher list
- **No attestation API**

#### Verdict

Bitbucket would require manual GPG signing and traditional verification
approaches. Not recommended as a pyscv target until Atlassian adds
Fulcio-compatible OIDC.

---

### Codeberg / Gitea / Forgejo

**Overall: GitHub-compatible APIs, but OIDC support is the blocker.**

#### Release Assets API

Gitea (and Forgejo, which powers Codeberg) has a GitHub-compatible
Releases API:

```
GET /api/v1/repos/{owner}/{repo}/releases/tags/{tag}
```

Release assets are returned in the same structure as GitHub:
```json
{
  "assets": [
    {
      "name": "file.whl",
      "browser_download_url": "https://codeberg.org/..."
    }
  ]
}
```

**Key differences:**
- API path is `/api/v1/` instead of GitHub's implicit API routing
- Asset download URLs use the instance hostname
- Self-hosted instances have arbitrary hostnames — ALLOWED_HOSTS must be configurable

**Refs:**
- https://codeberg.org/api/swagger
- https://gitea.com/api/swagger

#### CI/CD OIDC

**Gitea Actions (introduced in Gitea 1.19) does not yet support OIDC tokens.**

This is tracked in:
- https://github.com/go-gitea/gitea/issues/23299

Forgejo has a parallel tracking issue. Without OIDC, sigstore keyless signing
and PyPI trusted publishing are not possible.

**Workaround:** Use an external CI system (e.g., Woodpecker CI with
OIDC plugin) that can issue tokens.

#### Sigstore / SLSA / PyPI

All blocked by the lack of OIDC:
- **No sigstore keyless signing** from Gitea Actions
- **No SLSA provenance** (no hardened builder)
- **No PyPI trusted publishing** (PyPI doesn't accept Gitea as a publisher)

#### Verdict

The release API is usable for downloading artifacts, but verification
would be limited to checksums and GPG signatures until OIDC lands.
Worth supporting for download-only mode.

---

### SourceHut

**Overall: Fundamentally different philosophy. Lowest priority.**

#### Release Assets

SourceHut has no releases API. The project distribution model is:

- Source tarballs via `git.sr.ht/{user}/{repo}/refs` (tag listing)
- No binary artifact hosting
- Users are expected to publish to package registries directly

#### CI/CD (builds.sr.ht)

SourceHut's build system uses a custom manifest format (`.build.yml`).
**No OIDC support.** No plans for OIDC — SourceHut's philosophy favors
PGP/SSH-based identity.

#### Signing

SourceHut uses **PGP signing** for commits and tags. No sigstore integration.
The verification model is web-of-trust, not OIDC-based.

#### Verdict

SourceHut projects can only be verified through PyPI-only mode (download
from PyPI, verify PyPI attestations). No platform-specific integration
is feasible.

---

### Google Cloud Build

**Overall: Not a forge, but a relevant CI backend with full SCV support.**

Google Cloud Build is a CI/CD service that can be triggered from any
git platform. It provides:

- **OIDC tokens** via Workload Identity Federation
- **SLSA L3 provenance** via the Cloud Build provenance generator
- **Sigstore signing** — GCP OIDC tokens are accepted by Fulcio
- **PyPI trusted publishing** — Google Cloud is an accepted publisher

OIDC issuer: `https://accounts.google.com`

This is relevant as a "CI backend" paired with GitLab, Codeberg, or any
forge. A project hosted on Codeberg could use Cloud Build for CI and get
full SCV support.

**Refs:**
- https://cloud.google.com/build/docs/securing-builds/generate-provenance
- https://docs.pypi.org/trusted-publishers/adding-a-publisher/

---

## Cross-Cutting Concerns

### PyPI Trusted Publishing

PyPI's trusted publisher support as of early 2026:

| Publisher | Status | OIDC Issuer |
|-----------|--------|-------------|
| GitHub Actions | Supported | `token.actions.githubusercontent.com` |
| GitLab CI/CD | Supported | `gitlab.com` (or self-hosted) |
| Google Cloud Build | Supported | `accounts.google.com` |
| ActiveState | Supported | `platform.activestate.com` |
| Bitbucket Pipelines | **Not supported** | N/A (tokens not compatible) |
| Gitea/Forgejo Actions | **Not supported** | N/A (no OIDC yet) |
| SourceHut builds | **Not supported** | N/A (no OIDC) |

**Refs:**
- https://docs.pypi.org/trusted-publishers/
- https://peps.python.org/pep-0740/ (PEP 740 — Index Attestations)

### Sigstore OIDC Issuers

Fulcio (sigstore's CA) accepts tokens from these OIDC issuers:

| Issuer | URL | Notes |
|--------|-----|-------|
| GitHub | `token.actions.githubusercontent.com` | Default for GitHub Actions |
| GitLab | `gitlab.com` | Also self-hosted instances (configurable) |
| Google | `accounts.google.com` | For GCP workloads |
| Microsoft | `login.microsoftonline.com` | For Azure workloads |
| Chainguard | `issuer.enforce.dev` | Chainguard's identity service |
| Kubernetes | Cluster-specific | Via SPIFFE/SPIRE |

Self-hosted GitLab instances can be added to Fulcio's configuration,
but this requires coordination with the sigstore project.

**Refs:**
- https://docs.sigstore.dev/certificate_authority/oidc-in-fulcio/
- https://github.com/sigstore/fulcio/blob/main/config/fulcio-config.yaml

### SLSA Framework Support

| Builder | SLSA Level | Platform |
|---------|------------|----------|
| `slsa-framework/slsa-github-generator` | L3 | GitHub Actions only |
| Google Cloud Build | L3 | GCP (any trigger source) |
| `slsa-framework/slsa-verifier` | Verifier | Multi-platform (verifies provenance from any builder) |
| Tekton Chains | L3 | Kubernetes (any trigger) |
| FRSCA | L2-L3 | Kubernetes |

**Key insight:** SLSA L3 generation is tightly coupled to the build service.
Only GitHub Actions and Google Cloud Build have production-ready L3 generators.
GitLab has L1-L2 via manual in-toto provenance but no hardened L3 builder.

**Refs:**
- https://slsa.dev/spec/v1.0/verifying-artifacts
- https://github.com/slsa-framework/slsa-verifier
- https://cloud.google.com/build/docs/securing-builds/generate-provenance

---

## Comparison Matrix

| Feature | GitHub | GitLab | Bitbucket | Codeberg/Gitea | SourceHut | GCP Cloud Build |
|---------|--------|--------|-----------|----------------|-----------|-----------------|
| Release Assets API | Yes | Yes | Partial (Downloads) | Yes (compatible) | No | N/A (CI only) |
| CI/CD OIDC | Yes | Yes | Cloud-only | No (planned) | No | Yes |
| Fulcio-accepted OIDC | Yes | Yes | No | No | No | Yes |
| Sigstore keyless signing | Yes | Yes | No | No | No | Yes |
| SLSA L3 provenance | Yes | No (L1-L2) | No | No | No | Yes |
| PyPI trusted publishing | Yes | Yes | No | No | No | Yes |
| PEP 740 attestations | Yes | Yes | No | No | No | Yes |
| Attestation API | Yes (gh) | No | No | No | No | No |
| Self-hosted support | GHES | Yes | Cloud only | Yes | Yes | No |
| **pyscv priority** | **Done** | **High** | **Low** | **Medium** | **Low** | **Medium** |

---

## Architecture Recommendations

### Provider Abstraction

pyscv should define a `PlatformProvider` protocol:

```python
class PlatformProvider(Protocol):
    """Abstract interface for platform-specific operations."""

    def fetch_release_assets(self, tag: str) -> list[AssetInfo]: ...
    def download_asset(self, asset: AssetInfo, dest: Path) -> None: ...
    def allowed_hosts(self) -> frozenset[str]: ...
    def oidc_issuer(self) -> str | None: ...
    def identity_pattern(self, config: PyscvConfig) -> str | None: ...
```

With concrete implementations:
- `GitHubProvider` — current implementation, extracted
- `GitLabProvider` — Releases API + Generic Package Registry
- `GiteaProvider` — compatible with GitHub but different API base
- `PyPIOnlyProvider` — for platforms without release assets

### Verification Strategy

Not all platforms support all verification methods. pyscv should
support a **verification chain** that degrades gracefully:

```
Full verification (GitHub, GitLab+GCP):
  sigstore → SLSA L3 → PEP 740 → checksums

Partial verification (GitLab native):
  sigstore → in-toto L1-L2 → PEP 740 → checksums

Download-only (Codeberg, SourceHut):
  PEP 740 (from PyPI) → checksums

Minimal (Bitbucket):
  checksums only
```

### Configuration Model

Extend `[tool.pyscv]` to support platform selection:

```toml
[tool.pyscv]
platform = "github"  # github | gitlab | gitea | pypi-only
repo-slug = "owner/repo"

# GitLab-specific
# gitlab-url = "https://gitlab.com"
# gitlab-project-id = 12345

# Gitea-specific
# gitea-url = "https://codeberg.org"

# Verification chain
# verify = ["sigstore", "slsa", "pep740", "checksums"]
```

### ALLOWED_HOSTS

The current hardcoded `ALLOWED_HOSTS` frozenset must become configurable
per platform. Each provider declares its own allowed hosts, and
self-hosted instances add their own:

```python
# GitHub (fixed)
{"api.github.com", "github.com", "objects.githubusercontent.com", ...}

# GitLab (configurable base)
{"gitlab.com", "*.gitlab.com"}  # or self-hosted: {"git.example.com"}

# Codeberg/Gitea (configurable)
{"codeberg.org"}  # or self-hosted: {"gitea.example.com"}
```

---

## Implementation Roadmap

### Phase 1: Provider Abstraction (prerequisite)

Extract current GitHub-specific code into a `GitHubProvider` class.
Define the `PlatformProvider` protocol. This is pure refactoring with
no new platform support.

### Phase 2: GitLab Support (highest value)

- Implement `GitLabProvider` with Releases API + Package Registry
- Support GitLab OIDC issuer in identity verification
- Support self-hosted GitLab URLs
- Test with real GitLab CI pipelines

### Phase 3: PyPI-Only Mode

- Implement `PyPIOnlyProvider` that only downloads from PyPI
- Verification via PEP 740 attestations + checksums only
- Enables basic support for any platform (Codeberg, SourceHut, etc.)

### Phase 4: Gitea/Codeberg Support

- Implement `GiteaProvider` (mostly GitHub-compatible API)
- Monitor Gitea OIDC issue (go-gitea/gitea#23299)
- Initially download-only, upgrade to full verification when OIDC lands

### Phase 5: Future

- Google Cloud Build as CI backend (any forge)
- Tekton Chains integration (Kubernetes)
- Monitor Bitbucket OIDC evolution

---

## References

### Platform Documentation

- GitHub Releases API: https://docs.github.com/en/rest/releases
- GitHub Actions OIDC: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect
- GitLab Releases API: https://docs.gitlab.com/ee/api/releases/
- GitLab CI OIDC: https://docs.gitlab.com/ee/ci/secrets/id_token_authentication.html
- GitLab Trusted Publishing: https://blog.pypi.org/posts/2024-03-29-gitlab-trusted-publishers/
- Bitbucket Downloads API: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-downloads/
- Gitea API: https://gitea.com/api/swagger
- Gitea OIDC tracking: https://github.com/go-gitea/gitea/issues/23299

### Supply-Chain Standards

- SLSA specification: https://slsa.dev/spec/v1.0/
- SLSA GitHub generator: https://github.com/slsa-framework/slsa-github-generator
- SLSA verifier: https://github.com/slsa-framework/slsa-verifier
- PEP 740 (Index Attestations): https://peps.python.org/pep-0740/
- in-toto specification: https://in-toto.io/

### Sigstore

- Sigstore documentation: https://docs.sigstore.dev/
- Fulcio OIDC configuration: https://docs.sigstore.dev/certificate_authority/oidc-in-fulcio/
- Fulcio config (issuer list): https://github.com/sigstore/fulcio/blob/main/config/fulcio-config.yaml
- sigstore-python: https://github.com/sigstore/sigstore-python
- cosign: https://github.com/sigstore/cosign

### PyPI

- Trusted Publishers: https://docs.pypi.org/trusted-publishers/
- pypi-attestations library: https://github.com/trailofbits/pypi-attestations

### GitLab SLSA Tracking

- GitLab SLSA epic: https://gitlab.com/groups/gitlab-org/-/epics/9253
