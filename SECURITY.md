# Security Policy

## Supported Versions

Only the latest release of geek42 receives security fixes.

| Version | Supported |
|---------|-----------|
| latest  | ✅        |
| older   | ❌        |

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Report privately via one of the following channels, in order of preference:

1. **GitHub Private Vulnerability Reporting**
   Use the "Report a vulnerability" button on the [Security tab](https://github.com/OWNER/geek42/security/advisories/new)
   of this repository. This creates a private advisory visible only to
   maintainers.

2. **Encrypted email**
   Send to `security@example.org` (update with real contact) encrypted with
   the maintainer's public key published at `https://github.com/OWNER.gpg`.

Please include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept if possible)
- Affected versions
- Your name and affiliation (optional, for credit)
- Whether you plan to disclose publicly and on what timeline

## Response SLA

- **Triage**: within 7 days of report
- **Fix + advisory**: within 90 days for high/critical issues
- **Public disclosure**: coordinated with reporter, typically after a fix is
  released

If we fail to respond in 7 days, feel free to follow up publicly on the
Security tab.

## Scope

**In scope:**

- Remote code execution or sandbox escape from parsing malicious news items
- Directory traversal via crafted item IDs, paths, or config
- Denial of service through resource exhaustion
- Privilege escalation via the CLI
- Supply-chain compromise of published artifacts

**Out of scope:**

- Vulnerabilities in dependencies (report those upstream; we will update
  promptly via Dependabot)
- Issues in third-party news repositories themselves
- Network or DNS attacks on git clone operations (mitigate with HTTPS and
  known-hosts)
- Social engineering of maintainers

## Verifying Releases

All geek42 releases are:

- Built by GitHub Actions from a tagged commit
- Published to PyPI via **trusted publishing (OIDC)** — no long-lived tokens
- **Signed with sigstore** (keyless signing, bundle attached to release)
- Accompanied by **SLSA Level 3 build provenance**
- Accompanied by a **CycloneDX SBOM**

### Verify a wheel

```sh
# Download the wheel and the sigstore bundle from GitHub Releases or PyPI
pip download --no-deps geek42
gh release download v0.1.0 --pattern '*.sigstore'

# Verify the signature (Sigstore) — requires `uv tool install sigstore`
uv tool run sigstore verify identity \
    --cert-identity-regexp '^https://github\.com/OWNER/geek42/\.github/workflows/release\.yml@' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    --bundle geek42-0.1.0-py3-none-any.whl.sigstore \
    geek42-0.1.0-py3-none-any.whl

# Verify GitHub attestation (provenance)
gh attestation verify geek42-0.1.0-py3-none-any.whl --owner OWNER

# Verify SLSA provenance
slsa-verifier verify-artifact \
    --provenance-path geek42-0.1.0.intoto.jsonl \
    --source-uri github.com/OWNER/geek42 \
    --source-tag v0.1.0 \
    geek42-0.1.0-py3-none-any.whl
```

## Safe Harbor

We support responsible security research. If you follow this policy, we
will not pursue legal action against you. Good-faith efforts include:

- Avoiding privacy violations, data destruction, and service disruption
- Only interacting with test accounts or systems you own
- Giving us reasonable time to fix before disclosure

Thank you for helping keep geek42 and its users safe.
