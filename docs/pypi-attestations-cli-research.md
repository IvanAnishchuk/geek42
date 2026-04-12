# pypi-attestations CLI Research (Issue #36)

## Installed version

pypi-attestations 0.0.29 (already a dev dependency)

## CLI interface

Invocation: `pypi-attestations <command>` or `python -m pypi_attestations <command>`

### Subcommands

| Command | Purpose | Status |
|---------|---------|--------|
| `verify attestation` | Verify a local `.publish.attestation` file against an artifact | Works |
| `verify pypi` | Download + verify a package directly from PyPI | Production PyPI only (no TestPyPI) |
| `inspect` | Display attestation structure (statement, cert, tlog) | Works |
| `convert` | Convert a Sigstore bundle into a PEP 740 attestation | Works |
| `sign` | Sign artifacts | Not needed for verification |

### verify attestation

```sh
pypi-attestations verify attestation \
  --identity "https://github.com/IvanAnishchuk/geek42/.github/workflows/release.yml@refs/tags/v0.4.2a7" \
  dist/geek42-0.4.2a7-py3-none-any.whl
# OK: dist/geek42-0.4.2a7-py3-none-any.whl.publish.attestation
```

**File naming convention:** The CLI looks for `{artifact}.publish.attestation` or
`{artifact}.slsa.attestation` adjacent to the artifact. See
[`_cli.py:533`](https://github.com/pypi/pypi-attestations/blob/main/src/pypi_attestations/_cli.py#L533).

**Identity:** The `--identity` value must match the certificate SAN — the full
workflow URI including ref (e.g., `@refs/tags/v0.4.2a7`).

### inspect

```sh
pypi-attestations inspect dist/geek42-0.4.2a7-py3-none-any.whl.publish.attestation
pypi-attestations inspect --dump-bytes dist/geek42-0.4.2a7-py3-none-any.whl.publish.attestation
```

Output includes:
- Statement type and predicate type
- Subject name and digest
- Certificate SAN (suitable for `--identity`)
- Certificate issuer and validity
- Transparency log index

### verify pypi

```sh
pypi-attestations verify pypi \
  --repository https://github.com/IvanAnishchuk/geek42 \
  pypi:geek42-0.4.2a7-py3-none-any.whl
```

**Limitation:** Hardcoded to `files.pythonhosted.org` — rejects
`test.files.pythonhosted.org`. Not usable for TestPyPI releases.

## Key discovery: format mismatch

PyPI Integrity API returns a **provenance wrapper**:

```json
{
  "attestation_bundles": [
    {
      "publisher": {"kind": "GitHub", "repository": "...", "workflow": "..."},
      "attestations": [
        {"envelope": {...}, "verification_material": {...}, "version": 1}
      ]
    }
  ],
  "version": 1
}
```

The CLI expects individual PEP 740 `Attestation` objects (just the inner dict
with `envelope`, `verification_material`, `version` at top level).

**Extraction required:**

```python
import json
provenance = json.load(open("provenance.json"))
attestation = provenance["attestation_bundles"][0]["attestations"][0]
json.dump(attestation, open("artifact.publish.attestation", "w"))
```

## Stability warning

The pypi-attestations README states:

> The pypi-attestations CLI is intended primarily for experimentation,
> and is not considered a stable interface for generating or verifying
> attestations.

The version (0.0.x) reinforces this. However, for `verify_provenance.py`
(which already shells out to multiple CLI tools), this is acceptable —
the script is a verification demo, not a production installer.

## Other tools evaluated

| Tool | PEP 740 native? | CLI? | Stable? | Verdict |
|------|-----------------|------|---------|---------|
| `pypi-attestations` | Yes | Yes | No (0.0.x) | Best option for CLI approach |
| `trustcheck` | Yes | Yes | No (beta, 18 stars) | Too immature |
| `sigstore` CLI | No (bundles only) | Yes | Yes | Needs PEP 740 → bundle conversion |
| `cosign` | No (bundles only) | Yes | Yes | Same — needs conversion (verify_cosign.py does this) |
| `pip-plugin-pep740` | Yes | Transparent | No (5 stars) | Not ready |
| `uv` attestation | Planned | Planned | N/A | Tracked in astral-sh/uv#9122 |

## Conclusions

1. **`pypi-attestations` CLI is the only tool that can verify PEP 740
   attestations natively from the command line.** It's experimental but
   functional and already in our dependency tree.

2. **The extraction step** (provenance wrapper → individual attestation)
   should happen during proof download, making attestation files available
   for both CLI verification and manual inspection.

3. **`inspect` is valuable** for showing attestation details without
   needing to parse JSON manually — useful across all verify scripts.

4. **`verify_pure.py` should keep the Python library approach** — it
   exercises a different code path and doesn't need CLI subprocess calls.
