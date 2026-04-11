"""Verify all supply-chain security artifacts for a geek42 release.

This script checks four independent verification mechanisms:

1. SHA256 checksums    — basic integrity (SHA256SUMS.txt)
2. Sigstore signatures — keyless signing via OIDC (*.sigstore.json bundles)
3. GitHub attestations — build provenance stored in GitHub's attestation API
4. SLSA L3 provenance  — non-falsifiable provenance from an isolated builder

Each mechanism proves something different:

  SHA256       "The bytes haven't changed since the release."
  Sigstore     "This artifact was signed by the release workflow."
  GH Attests   "GitHub certifies this was built by this workflow at this commit."
  SLSA L3      "An isolated, tamper-proof builder produced this from that source."

Requirements:
  - gh         (GitHub CLI, for attestation verify + release download)
  - sigstore   (uv tool run sigstore, for sigstore bundle verification)
  - slsa-verifier (Go binary, for SLSA L3 provenance verification)
  - rich       (Python, for pretty output — already a project dependency)

Usage:
    uv run python scripts/verify_provenance.py [VERSION]
    uv run python scripts/verify_provenance.py 0.4.2a4
    uv run python scripts/verify_provenance.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_OWNER = "IvanAnishchuk"
REPO_NAME = "geek42"
REPO_SLUG = f"{REPO_OWNER}/{REPO_NAME}"
PACKAGE_NAME = "geek42"
DIST_EXTENSIONS = (".whl", ".tar.gz")

# -- Descriptions for each mechanism ----------------------------------

DESCRIPTIONS = {
    "sha256": (
        "[bold]SHA256 checksums[/] verify basic integrity.\n"
        "The release workflow computes SHA256 hashes of all artifacts and\n"
        "writes them to SHA256SUMS.txt. Anyone can re-hash the downloaded\n"
        "files and compare. This catches corruption or tampering in transit,\n"
        "but does NOT prove who built them."
    ),
    "sigstore": (
        "[bold]Sigstore signatures[/] prove the artifact was signed by the\n"
        "release workflow using keyless (OIDC) signing. The signature is\n"
        "recorded in the Rekor transparency log. Verification checks that\n"
        "the signer's certificate was issued to the expected GitHub Actions\n"
        "workflow identity. No long-lived keys are involved."
    ),
    "gh_attestation": (
        "[bold]GitHub attestations[/] (via actions/attest) store build\n"
        "provenance in GitHub's attestation API. They record WHAT was built,\n"
        "by WHICH workflow, at WHICH commit, and are signed via Sigstore.\n"
        "Verification uses 'gh attestation verify' which checks the\n"
        "signature and the artifact's SHA256 against the stored attestation."
    ),
    "slsa_l3": (
        "[bold]SLSA Level 3 provenance[/] is the strongest guarantee.\n"
        "Unlike GitHub attestations (which run in the same workflow),\n"
        "SLSA L3 uses an ISOLATED reusable workflow from\n"
        "slsa-framework/slsa-github-generator that the caller CANNOT\n"
        "tamper with. The provenance is a signed in-toto statement\n"
        "recording source, builder, and artifact digests. Verified with\n"
        "'slsa-verifier' (a Go binary from the SLSA framework)."
    ),
}


# -- Helpers -----------------------------------------------------------


def get_version() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].removeprefix("v")
    init = REPO_ROOT / "src" / "geek42" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    console.print("[red]Could not detect version. Pass it as an argument.[/]")
    sys.exit(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)  # noqa: S603


def is_dist_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in DIST_EXTENSIONS)


def header(title: str) -> None:
    console.print()
    console.rule(f"[bold blue]{title}[/]")
    console.print()


def ok(msg: str) -> None:
    console.print(f"  [bold green]OK[/] {msg}")


def fail(msg: str) -> None:
    console.print(f"  [bold red]FAIL[/] {msg}")


def info(msg: str) -> None:
    console.print(f"  [dim]{msg}[/]")


def explain(key: str) -> None:
    console.print(Panel(DESCRIPTIONS[key], border_style="dim"))


# -- Collectors --------------------------------------------------------


def collect_local(version: str) -> dict[str, Path]:
    dist_dir = REPO_ROOT / "dist"
    if not dist_dir.is_dir():
        return {}
    return {
        f.name: f
        for f in sorted(dist_dir.iterdir())
        if is_dist_file(f.name) and version in f.name
    }


def download_github_release(version: str, dest: Path) -> dict[str, Path]:
    tag = f"v{version}"
    result = run(["gh", "release", "download", tag, "--repo", REPO_SLUG, "--dir", str(dest)])
    if result.returncode != 0:
        console.print(f"  [yellow]GitHub Release {tag} not found or download failed[/]")
        if result.stderr:
            info(result.stderr.strip())
        return {}
    return {f.name: f for f in sorted(dest.iterdir()) if is_dist_file(f.name)}


def download_pypi(version: str, dest: Path) -> dict[str, Path]:
    for index_name, extra_args in [
        ("TestPyPI", ["--index-url", "https://test.pypi.org/simple/",
                       "--extra-index-url", "https://pypi.org/simple/"]),
        ("PyPI", []),
    ]:
        result = run(
            ["pip", "download", "--no-deps", *extra_args,
             "--dest", str(dest), f"{PACKAGE_NAME}=={version}"]
        )
        if result.returncode == 0:
            info(f"Downloaded from {index_name}")
            break
    else:
        console.print(f"  [yellow]Download failed for {PACKAGE_NAME}=={version}[/]")
        return {}
    run(["pip", "download", "--no-deps", "--no-binary", ":all:",
         *extra_args, "--dest", str(dest), f"{PACKAGE_NAME}=={version}"])
    return {f.name: f for f in sorted(dest.iterdir()) if is_dist_file(f.name)}


# -- 1. SHA256 checksums ----------------------------------------------


def verify_checksums(artifacts: dict[str, Path], sums_file: Path | None) -> bool:
    expected: dict[str, str] = {}
    if sums_file and sums_file.exists():
        for line in sums_file.read_text().splitlines():
            if line.strip():
                h, name = line.split(None, 1)
                expected[name.strip()] = h.strip()

    all_ok = True
    for name, path in sorted(artifacts.items()):
        actual = sha256(path)
        if name in expected:
            if actual == expected[name]:
                ok(f"{name}: {actual}")
            else:
                fail(f"{name}: expected {expected[name]}, got {actual}")
                all_ok = False
        else:
            info(f"{name}: {actual}")
    return all_ok


# -- 2. Sigstore signatures -------------------------------------------


def _extract_san_from_bundle(bundle_path: Path) -> str | None:
    try:
        bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
        cert_b64 = (
            bundle_data.get("verificationMaterial", {}).get("certificate", {}).get("rawBytes", "")
        )
        if not cert_b64:
            return None
        cert_pem = "-----BEGIN CERTIFICATE-----\n" + cert_b64 + "\n-----END CERTIFICATE-----\n"
        result = run(["openssl", "x509", "-noout", "-ext", "subjectAltName"], input=cert_pem)
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("URI:"):
                return stripped.removeprefix("URI:")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def verify_sigstore(path: Path, bundle: Path | None, version: str) -> bool:
    if not bundle or not bundle.exists():
        info(f"sigstore: no bundle for {path.name}")
        return True

    san = _extract_san_from_bundle(bundle)
    if not san:
        san = (
            f"https://github.com/{REPO_SLUG}"
            f"/.github/workflows/release.yml@refs/tags/v{version}"
        )

    result = run([
        "uv", "tool", "run", "sigstore", "verify", "identity",
        "--cert-identity", san,
        "--cert-oidc-issuer", "https://token.actions.githubusercontent.com",
        "--bundle", str(bundle),
        str(path),
    ])
    if result.returncode != 0:
        fail(f"sigstore verify: {result.stderr.strip()}")
        return False
    ok(f"sigstore verify: {path.name}")
    return True


# -- 3. GitHub attestations -------------------------------------------


def verify_gh_attestation(path: Path) -> dict | None:
    result = run(["gh", "attestation", "verify", str(path), "--repo", REPO_SLUG, "--format", "json"])
    if result.returncode != 0:
        fail(f"gh attestation verify: {result.stderr.strip()}")
        return None
    ok(f"gh attestation verify: {path.name}")
    try:
        records = json.loads(result.stdout)
        if isinstance(records, list) and records:
            return records[0]
    except json.JSONDecodeError:
        pass
    return None


def print_gh_attestation_details(attestation: dict) -> None:
    vr = attestation.get("verificationResult", {})
    cert = vr.get("signature", {}).get("certificate", {})
    stmt = vr.get("statement", {})
    predicate = stmt.get("predicate", {})
    build_def = predicate.get("buildDefinition", {})
    run_details = predicate.get("runDetails", {})
    workflow = build_def.get("externalParameters", {}).get("workflow", {})
    resolved = build_def.get("resolvedDependencies", [])
    timestamps = vr.get("verifiedTimestamps", [])

    table = Table(title="GitHub Attestation", show_header=False, padding=(0, 2), expand=True)
    table.add_column("Field", style="bold cyan", min_width=24, max_width=30)
    table.add_column("Value", overflow="fold")

    table.add_row("Predicate type", stmt.get("predicateType", "?"))
    table.add_row("Build type", build_def.get("buildType", "?"))
    table.add_row("Workflow", workflow.get("path", "?"))
    table.add_row("Workflow ref", workflow.get("ref", "?"))
    table.add_row("Source repo", workflow.get("repository", "?"))
    if resolved:
        dep = resolved[0]
        table.add_row("Source URI", dep.get("uri", "?"))
        table.add_row("Source commit", dep.get("digest", {}).get("gitCommit", "?"))
    table.add_row("Builder ID", run_details.get("builder", {}).get("id", "?"))
    table.add_row("Invocation", run_details.get("metadata", {}).get("invocationId", "?"))

    github = build_def.get("internalParameters", {}).get("github", {})
    table.add_row("Event", github.get("event_name", "?"))
    table.add_row("Runner", github.get("runner_environment", "?"))

    table.add_row("", "")
    table.add_row("Issuer", cert.get("certificateIssuer", "?"))
    table.add_row("OIDC issuer", cert.get("issuer", "?"))
    table.add_row("SAN", cert.get("subjectAlternativeName", "?"))
    table.add_row("Trigger", cert.get("githubWorkflowTrigger", "?"))

    if timestamps:
        ts = timestamps[0]
        table.add_row("Log timestamp", ts.get("timestamp", "?"))

    subjects = stmt.get("subject", [])
    if subjects:
        table.add_row("", "")
        for subj in subjects:
            digest = subj.get("digest", {}).get("sha256", "?")
            table.add_row(subj.get("name", "?"), f"sha256:{digest}")

    console.print()
    console.print(table)


# -- 4. SLSA L3 provenance --------------------------------------------


def _find_slsa_verifier() -> str:
    """Find slsa-verifier binary, checking common install locations."""
    import shutil

    path = shutil.which("slsa-verifier")
    if path:
        return path
    go_bin = Path.home() / "go" / "bin" / "slsa-verifier"
    if go_bin.exists():
        return str(go_bin)
    return "slsa-verifier"  # let it fail with a clear error


def verify_slsa_provenance(artifact: Path, provenance: Path, version: str) -> bool:
    tag = f"v{version}"
    verifier = _find_slsa_verifier()
    result = run([
        verifier, "verify-artifact",
        "--provenance-path", str(provenance),
        "--source-uri", f"github.com/{REPO_SLUG}",
        "--source-tag", tag,
        "--print-provenance",
        str(artifact),
    ])
    if result.returncode != 0:
        fail(f"slsa-verifier: {result.stderr.strip()}")
        return False
    ok(f"slsa-verifier: {artifact.name}")

    for line in result.stdout.splitlines():
        try:
            print_slsa_provenance(json.loads(line))
            break
        except json.JSONDecodeError:
            continue
    return True


def print_slsa_provenance(data: dict) -> None:
    pred = data.get("predicate", {})
    cs = pred.get("invocation", {}).get("configSource", {})
    env = pred.get("invocation", {}).get("environment", {})
    meta = pred.get("metadata", {})

    table = Table(title="SLSA L3 Provenance", show_header=False, padding=(0, 2), expand=True)
    table.add_column("Field", style="bold cyan", min_width=24, max_width=30)
    table.add_column("Value", overflow="fold")

    table.add_row("Statement type", data.get("_type", "?"))
    table.add_row("Predicate type", data.get("predicateType", "?"))
    table.add_row("Builder ID", pred.get("builder", {}).get("id", "?"))
    table.add_row("Build type", pred.get("buildType", "?"))
    table.add_row("", "")
    table.add_row("Source URI", cs.get("uri", "?"))
    table.add_row("Source commit", cs.get("digest", {}).get("sha1", "?"))
    table.add_row("Entry point", cs.get("entryPoint", "?"))
    table.add_row("", "")
    table.add_row("Actor", env.get("github_actor", "?"))
    table.add_row("Event", env.get("github_event_name", "?"))
    table.add_row("Ref", env.get("github_ref", "?"))
    table.add_row("Run ID", env.get("github_run_id", "?"))
    table.add_row("Commit SHA", env.get("github_sha1", "?"))
    table.add_row("Invocation ID", meta.get("buildInvocationID", "?"))
    table.add_row("Reproducible", str(meta.get("reproducible", "?")))

    materials = pred.get("materials", [])
    if materials:
        table.add_row("", "")
        for m in materials:
            table.add_row("Material", f"{m.get('uri', '?')}  sha1:{m.get('digest', {}).get('sha1', '?')}")

    subjects = data.get("subject", [])
    if subjects:
        table.add_row("", "")
        for subj in subjects:
            digest = subj.get("digest", {}).get("sha256", "?")
            table.add_row(subj.get("name", "?"), f"sha256:{digest}")

    console.print()
    console.print(table)


# -- Cross-source comparison ------------------------------------------


def compare_hashes(sources: dict[str, dict[str, str]]) -> bool:
    all_names: set[str] = set()
    for hashes in sources.values():
        all_names.update(hashes)

    all_match = True
    table = Table(title="Cross-source Hash Comparison", expand=True)
    table.add_column("Artifact", style="bold", overflow="fold")
    for source in sources:
        table.add_column(source)

    for name in sorted(all_names):
        row: list[str] = [name]
        values: set[str] = set()
        for source in sources:
            h = sources[source].get(name, "")
            row.append(h[:16] + "..." if h else "[dim]n/a[/]")
            if h:
                values.add(h)
        if len(values) > 1:
            all_match = False
            row[0] = f"[red]{name}[/]"
        table.add_row(*row)

    console.print()
    console.print(table)
    if all_match:
        ok("All hashes match across sources")
    else:
        fail("Hash mismatch detected between sources!")
    return all_match


# -- Main --------------------------------------------------------------


def main() -> int:
    version = get_version()
    console.print(Panel(f"Verifying supply-chain security for [bold]{PACKAGE_NAME} {version}[/]"))

    failures = 0
    source_hashes: dict[str, dict[str, str]] = {}

    # -- Local dist/ ---------------------------------------------------
    header("Local dist/")
    local = collect_local(version)
    if local:
        console.print(f"  Found {len(local)} artifact(s)")
        local_sums = REPO_ROOT / "dist" / "SHA256SUMS.txt"
        verify_checksums(local, local_sums if local_sums.exists() else None)
        source_hashes["local"] = {n: sha256(p) for n, p in local.items()}
    else:
        info("No local artifacts found in dist/")

    with tempfile.TemporaryDirectory(prefix="verify-") as tmpdir:
        tmp = Path(tmpdir)

        # -- GitHub Release --------------------------------------------
        header("GitHub Release")
        gh_dir = tmp / "github"
        gh_dir.mkdir()
        gh_artifacts = download_github_release(version, gh_dir)
        if gh_artifacts:
            console.print(f"  Found {len(gh_artifacts)} artifact(s)")

            # 1. SHA256 checksums
            header("1. SHA256 checksums")
            explain("sha256")
            gh_sums = gh_dir / "SHA256SUMS.txt"
            verify_checksums(gh_artifacts, gh_sums)
            source_hashes["github"] = {n: sha256(p) for n, p in gh_artifacts.items()}

            # 2. Sigstore signatures
            header("2. Sigstore signatures")
            explain("sigstore")
            for name, path in gh_artifacts.items():
                # Try both .sigstore.json and .sigstore extensions
                bundle = gh_dir / f"{name}.sigstore.json"
                if not bundle.exists():
                    bundle = gh_dir / f"{name}.sigstore"
                verify_sigstore(path, bundle, version)

            # 3. GitHub attestations
            header("3. GitHub attestations")
            explain("gh_attestation")
            attestation_shown = False
            for name, path in gh_artifacts.items():
                att = verify_gh_attestation(path)
                if att and not attestation_shown:
                    print_gh_attestation_details(att)
                    attestation_shown = True

            # 4. SLSA L3 provenance
            provenance = gh_dir / "geek42-provenance.intoto.jsonl"
            header("4. SLSA L3 provenance")
            explain("slsa_l3")
            if provenance.exists():
                for name, path in gh_artifacts.items():
                    if not verify_slsa_provenance(path, provenance, version):
                        failures += 1
                    break  # show details once
            else:
                info("No provenance file in release (geek42-provenance.intoto.jsonl)")
                info("The provenance may be in the workflow artifacts instead.")
        else:
            info("No GitHub Release artifacts available")

        # -- PyPI / TestPyPI -------------------------------------------
        header("PyPI / TestPyPI")
        pypi_dir = tmp / "pypi"
        pypi_dir.mkdir()
        pypi_artifacts = download_pypi(version, pypi_dir)
        if pypi_artifacts:
            console.print(f"  Found {len(pypi_artifacts)} artifact(s)")
            source_hashes["pypi"] = {n: sha256(p) for n, p in pypi_artifacts.items()}
            for name in sorted(pypi_artifacts):
                info(f"{name}: {source_hashes['pypi'][name]}")
            # Verify GitHub attestations for PyPI artifacts too
            for name, path in pypi_artifacts.items():
                verify_gh_attestation(path)
            # Verify SLSA L3 provenance for PyPI artifacts (using GH Release provenance)
            provenance = gh_dir / "geek42-provenance.intoto.jsonl"
            if provenance.exists():
                for name, path in pypi_artifacts.items():
                    verify_slsa_provenance(path, provenance, version)
        else:
            info("No PyPI/TestPyPI artifacts available")

    # -- Cross-source comparison ---------------------------------------
    if len(source_hashes) > 1:
        header("Cross-source comparison")
        if not compare_hashes(source_hashes):
            failures += 1

    # -- Summary -------------------------------------------------------
    console.print()
    if failures:
        console.print(Panel("[bold red]Verification completed with failures[/]"))
        return 1
    console.print(Panel("[bold green]All verifications passed[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
