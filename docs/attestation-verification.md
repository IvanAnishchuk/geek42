# Package Attestation Verification: State of the Art (April 2026)

## What geek42 produces

Every release generates five independent verification artifacts:

| Artifact | Tool | What it proves |
|----------|------|---------------|
| `geek42-{ver}-SHA256SUMS.txt` | sha256sum | Bytes haven't changed since release |
| `*.sigstore.json` | [sigstore](https://www.sigstore.dev/) | Artifact was signed by the release workflow (keyless OIDC) |
| GitHub attestation | [actions/attest](https://github.com/actions/attest) | GitHub certifies this was built by this workflow at this commit |
| `geek42-v{ver}-provenance.intoto.jsonl` | [slsa-github-generator](https://github.com/slsa-framework/slsa-github-generator) | An isolated, tamper-proof builder produced this from that source (SLSA L3) |
| PyPI publish attestation | [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) | PyPI received this from the expected Trusted Publisher (PEP 740) |

## Consumer-side verification today

### Three verification scripts

geek42 provides three verification scripts with **full parity** — all five
providers are verified by each script using different toolchains:

| Script | Dependencies | Best for |
|--------|-------------|----------|
| `verify_provenance.py` | gh, sigstore CLI, slsa-verifier, pypi-attestations CLI | Most verbose, each tool native |
| `verify_cosign.py` | cosign, pypi-attestations CLI (inspect only), gh (for proof download) | Single verification binary |
| `verify_pure.py` | sigstore + pypi-attestations (Python library), gh (for proof download) | Minimal external tools |

`gh` is required by all scripts for downloading proof files.
`verify_provenance.py` also uses `gh attestation verify` during verification.
For `verify_cosign.py` and `verify_pure.py`, `gh` is only needed if proofs
are not already in `proofs/github/` (e.g., from `download_release.py`).

**Quick start:**
```sh
# Download release artifacts + all proof files (GitHub, PyPI, TestPyPI)
uv run python scripts/download_release.py 0.4.2a7

# Verify with any of the three scripts
uv run python scripts/verify_provenance.py 0.4.2a7
uv run python scripts/verify_cosign.py 0.4.2a7
uv run python scripts/verify_pure.py 0.4.2a7
```

`download_release.py` fetches from three sources and extracts all proof formats:
- GitHub Release assets (sigstore bundles, SLSA provenance, checksums)
- GitHub Attestation API (build attestations + extracted sigstore bundles)
- PyPI/TestPyPI Integrity API (PEP 740 provenance + extracted `.publish.attestation`
  files and cosign-compatible bundles)

### Key finding: bundle format interoperability

GitHub attestations and PyPI PEP 740 attestations both contain standard
sigstore bundles inside wrapper formats. All three toolchains (dedicated
CLIs, cosign, Python sigstore library) can verify all five providers by
extracting the inner bundles:

| Provider | Wrapper format | Inner format | Verified by |
|----------|---------------|--------------|-------------|
| Sigstore bundles | sigstore bundle v0.3 | messageSignature | All three |
| GitHub attestations | `gh attestation verify` JSON array | dsseEnvelope | All three (extract `.attestation.bundle`) |
| SLSA L3 provenance | sigstore bundle v0.3 | dsseEnvelope | All three |
| PyPI PEP 740 | PyPI Integrity API JSON | dsseEnvelope + cert + tlog | All three (restructure to bundle format) |

### Hash verification via uv.lock (automatic)

- `uv.lock` stores SHA-256 hashes for every distribution
- `uv sync` verifies hashes on install automatically
- Protects against: tampering in transit, corrupted mirrors, MITM
- Does NOT protect against: malicious package uploaded through legitimate channels

### Individual tool verification

```sh
# Download release (dist files to dist/, proofs to proofs/github/)
uv run python scripts/download_release.py 0.4.2a7

# Sigstore bundle (cosign)
cosign verify-blob \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity 'https://github.com/IvanAnishchuk/geek42/.github/workflows/release.yml@refs/tags/v0.4.2a7' \
  --bundle proofs/github/geek42-0.4.2a7-py3-none-any.whl.sigstore.json \
  dist/geek42-0.4.2a7-py3-none-any.whl

# SLSA L3 provenance (cosign)
cosign verify-blob-attestation \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp 'https://github.com/slsa-framework/slsa-github-generator/' \
  --type slsaprovenance \
  --bundle proofs/github/geek42-v0.4.2a7-provenance.intoto.jsonl \
  dist/geek42-0.4.2a7-py3-none-any.whl

# GitHub attestation (gh CLI)
gh attestation verify dist/geek42-0.4.2a7-py3-none-any.whl --repo IvanAnishchuk/geek42

# SLSA L3 provenance (slsa-verifier)
slsa-verifier verify-artifact \
  --provenance-path proofs/github/geek42-v0.4.2a7-provenance.intoto.jsonl \
  --source-uri github.com/IvanAnishchuk/geek42 \
  --source-tag v0.4.2a7 \
  dist/geek42-0.4.2a7-py3-none-any.whl

# PyPI PEP 740 attestation (pypi-attestations CLI)
# Requires .publish.attestation file — created by download_release.py
pypi-attestations inspect dist/geek42-0.4.2a7-py3-none-any.whl.publish.attestation
pypi-attestations verify attestation \
  --identity 'https://github.com/IvanAnishchuk/geek42/.github/workflows/release.yml@refs/tags/v0.4.2a7' \
  dist/geek42-0.4.2a7-py3-none-any.whl
```

### What doesn't work yet

**Neither uv nor pip verify PEP 740 attestations at install time.**

There is no `--verify-attestations` flag. Consumer-side verification in standard
installers is the primary missing piece in the Python supply chain security story.

## uv attestation support roadmap

Active development tracked in [astral-sh/uv#9122](https://github.com/astral-sh/uv/issues/9122):

> "Yes, this is something I'm working on."
> — William Woodruff (@woodruffw), PEP 740 author, March 27, 2026

Proposed features:
- Display publisher identity when locking
- Warn/error on publisher identity changes during upgrades
- Configuration to pin packages to specific publishers (TOFU model)

The maintainers consider this "security sensitive" and may implement it in-house.

Separate issue [uv#15618](https://github.com/astral-sh/uv/issues/15618) tracks `uv publish`
creating attestations (producer side).

## pip attestation roadmap

Trail of Bits (PEP 740 authors) describe a three-phase plan:
1. **Short-term**: Plugin architecture for pip to load verification logic
2. **Medium-term**: "Trust on first use" (TOFU) identity tracking
3. **Long-term**: Lockfile integration via PEP 751, storing identity expectations alongside hashes

No public timeline announced.

## PyPI's PEP 740 system

### Producer side (live)

- `pypa/gh-action-pypi-publish` v1.11+ automatically generates Sigstore-signed attestations
- Attestations bind distributions to CI/CD identities via ephemeral Sigstore keys
- PyPI verifies attestations on upload, rejects invalid ones

### Index side (live)

- Distributions with attestations get a `provenance` key in the JSON Simple API
- [PyPI Integrity API](https://docs.pypi.org/attestations/) provides programmatic access
- As of March 2026: **132,360+ packages** have attestations, **17% of uploads** include them

### Consumer side (the gap)

- No standard installer verifies attestations automatically
- [Are we PEP 740 yet?](https://trailofbits.github.io/are-we-pep740-yet/) tracker says:
  "We're currently working on integrating attestation verification into installers
  like pip and uv. Once this happens, you won't need to do anything special — it
  will just work!"

## Third-party tools

### trustcheck

Community CLI tool for inspecting trust signals before installation:
```sh
pip install trustcheck
trustcheck inspect geek42
trustcheck inspect geek42 --expected-repo https://github.com/IvanAnishchuk/geek42
```
[GitHub: Halfblood-Prince/trustcheck](https://github.com/Halfblood-Prince/trustcheck) — currently in beta.

### pypi-attestations

Official library and CLI (Trail of Bits / PyPI) for PEP 740 attestation
verification. The CLI (v0.0.29) provides `verify attestation`, `inspect`,
and `convert` subcommands. geek42 uses the CLI in `verify_provenance.py`
and for `inspect` output in `verify_cosign.py`, while `verify_pure.py`
uses the Python library API.

```sh
# Verify a PEP 740 attestation (requires .publish.attestation file next to artifact)
pypi-attestations verify attestation \
  --identity 'https://github.com/IvanAnishchuk/geek42/.github/workflows/release.yml@refs/tags/v0.4.2a7' \
  dist/geek42-0.4.2a7-py3-none-any.whl

# Inspect attestation details (unverified display)
pypi-attestations inspect dist/geek42-0.4.2a7-py3-none-any.whl.publish.attestation
```

Note: The CLI is marked as experimental (v0.0.x). The `verify pypi` subcommand
only supports production PyPI, not TestPyPI.

[PyPI: pypi-attestations](https://pypi.org/project/pypi-attestations/)

### Google OSS Rebuild

Independently rebuilds packages from PyPI, compares artifacts, and publishes
SLSA Level 3 provenance. Organizations can deploy their own instances.
[GitHub: google/oss-rebuild](https://github.com/google/oss-rebuild)

## Comparison with npm

| Feature | npm | PyPI/pip/uv |
|---------|-----|-------------|
| Provenance generation | Automatic with Trusted Publishing | Automatic with `gh-action-pypi-publish` v1.11+ |
| Consumer verification CLI | `npm audit signatures` (built-in) | **None built-in** |
| Install-time enforcement | Signatures verified during `npm install` | **Not available** |
| Sigstore infrastructure | Fulcio + Rekor | Fulcio + Rekor (identical) |
| SLSA level | Level 3 | Level 3 |
| Adoption rate | ~7.2% of dependencies | ~17% of packages (higher) |
| Lockfile hashes | `package-lock.json` integrity | `uv.lock` SHA-256 (both verify) |

PyPI has higher producer-side adoption but npm has better consumer-side tooling.

## Practical recommendations for geek42 users

1. **Use `uv.lock`** — provides hash-based integrity on every install (automatic)
2. **Run `scripts/verify_provenance.py`** after downloading a release for full verification
3. **Use `gh attestation verify`** as a quick check for any downloaded wheel
4. **Consider `exclude-newer`** in `pyproject.toml` for a quarantine window on new packages
5. **Watch [uv#9122](https://github.com/astral-sh/uv/issues/9122)** for native attestation support

## References

- [PEP 740 — Index support for digital attestations](https://peps.python.org/pep-0740/)
- [PyPI Attestations Documentation](https://docs.pypi.org/attestations/)
- [Are we PEP 740 yet?](https://trailofbits.github.io/are-we-pep740-yet/)
- [Attestations: A new generation of signatures on PyPI](https://blog.trailofbits.com/2024/11/14/attestations-a-new-generation-of-signatures-on-pypi/) — Trail of Bits Blog
- [PyPI now supports digital attestations](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/) — PyPI Blog
- [uv#9122 — Incorporate PEP 740](https://github.com/astral-sh/uv/issues/9122)
- [uv#15618 — uv publish: create attestations](https://github.com/astral-sh/uv/issues/15618)
- [SLSA framework](https://slsa.dev/)
- [slsa-github-generator](https://github.com/slsa-framework/slsa-github-generator)
- [Sigstore](https://www.sigstore.dev/)
- [Google OSS Rebuild](https://github.com/google/oss-rebuild)
- [trustcheck](https://github.com/Halfblood-Prince/trustcheck)
- [Defense in Depth: Python Supply Chain Security](https://bernat.tech/posts/securing-python-supply-chain/)
