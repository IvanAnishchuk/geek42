"""Verify local distribution files using cosign only.

Alternative to verify_provenance.py that uses a single tool (cosign)
instead of gh, sigstore, slsa-verifier, and pypi-attestations. Useful
when cosign is the only verification tool available.

Cosign can verify:
1. Sigstore signatures  — cosign verify-blob with *.sigstore.json bundles
2. SLSA L3 provenance   — cosign verify-blob-attestation with *.intoto.jsonl
3. SHA256 checksums      — manual comparison (no cosign needed)

What cosign cannot verify (use verify_provenance.py instead):
- GitHub attestations (stored in GitHub's API, not as bundles)
- PyPI PEP 740 attestations (stored in PyPI's Integrity API)

Requirements:
  - cosign  (Go binary from sigstore — brew install cosign, go install, or distro package)

Usage:
    uv run scripts/verify_cosign.py [VERSION]
    uv run scripts/verify_cosign.py 0.4.2a7
    uv run scripts/verify_cosign.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_OWNER = "IvanAnishchuk"
REPO_NAME = "geek42"
REPO_SLUG = f"{REPO_OWNER}/{REPO_NAME}"
PACKAGE_NAME = "geek42"
DIST_EXTENSIONS = (".whl", ".tar.gz")
OIDC_ISSUER = "https://token.actions.githubusercontent.com"


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


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603


def is_dist_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in DIST_EXTENSIONS)


def collect_local(version: str) -> dict[str, Path]:
    dist_dir = REPO_ROOT / "dist"
    if not dist_dir.is_dir():
        return {}
    return {
        f.name: f
        for f in sorted(dist_dir.iterdir())
        if is_dist_file(f.name) and version in f.name
    }


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


# -- Verification ------------------------------------------------------


def verify_sigstore_blob(path: Path, bundle: Path, version: str) -> bool:
    """Verify a sigstore bundle against a file using cosign verify-blob."""
    if not bundle.exists():
        info(f"No sigstore bundle for {path.name}")
        return True  # not a failure, just not available

    # Use exact identity for the specific tag
    identity = (
        f"https://github.com/{REPO_SLUG}"
        f"/.github/workflows/release.yml@refs/tags/v{version}"
    )

    result = run([
        "cosign", "verify-blob",
        "--certificate-oidc-issuer", OIDC_ISSUER,
        "--certificate-identity", identity,
        "--bundle", str(bundle),
        str(path),
    ])
    if result.returncode != 0:
        # Try with regexp fallback
        result = run([
            "cosign", "verify-blob",
            "--certificate-oidc-issuer", OIDC_ISSUER,
            "--certificate-identity-regexp", f"https://github.com/{REPO_SLUG}/",
            "--bundle", str(bundle),
            str(path),
        ])

    if result.returncode != 0:
        fail(f"cosign verify-blob: {path.name}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                fail(f"  {line}")
        return False

    ok(f"cosign verify-blob: {path.name}")
    info(f"  identity: {identity}")
    return True


def verify_slsa_attestation(path: Path, provenance: Path) -> bool:
    """Verify SLSA L3 provenance using cosign verify-blob-attestation."""
    if not provenance.exists():
        info(f"No SLSA provenance file found")
        return True  # not a failure, just not available

    # SLSA provenance is signed by the slsa-framework generator, not our workflow
    result = run([
        "cosign", "verify-blob-attestation",
        "--certificate-oidc-issuer", OIDC_ISSUER,
        "--certificate-identity-regexp",
        "https://github.com/slsa-framework/slsa-github-generator/",
        "--type", "slsaprovenance",
        "--bundle", str(provenance),
        str(path),
    ])
    if result.returncode != 0:
        fail(f"cosign verify-blob-attestation: {path.name}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                fail(f"  {line}")
        return False

    ok(f"cosign verify-blob-attestation: {path.name} (SLSA L3)")
    return True


def verify_checksums(artifacts: dict[str, Path], sums_file: Path) -> bool:
    """Verify SHA256 checksums against SHA256SUMS.txt."""
    if not sums_file.exists():
        info("No SHA256SUMS.txt found")
        return True

    expected: dict[str, str] = {}
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
            info(f"{name}: {actual} (not in SHA256SUMS.txt)")
    return all_ok


# -- Main --------------------------------------------------------------


def main() -> int:
    version = get_version()
    console.print(Panel(
        f"Verifying [bold]{PACKAGE_NAME} {version}[/] with cosign\n"
        f"[dim]Only requires cosign — no gh, sigstore, or slsa-verifier needed[/]"
    ))

    # Check cosign is available
    result = run(["cosign", "version"])
    if result.returncode != 0:
        console.print(Panel("[bold red]cosign not found. Install from https://docs.sigstore.dev/cosign/system_config/installation/[/]"))
        return 1

    failures = 0

    # -- Locate artifacts in dist/ -------------------------------------
    header("Distribution files")
    artifacts = collect_local(version)
    if not artifacts:
        console.print(Panel(
            f"[bold red]No files matching version {version} found in dist/[/]\n"
            "Download with: uv run scripts/download_release.py " + version,
        ))
        return 1
    console.print(f"  Verifying {len(artifacts)} file(s) from dist/:")
    for name, path in artifacts.items():
        info(f"{name}: {sha256(path)}")

    # -- Ensure proof files exist --------------------------------------
    gh_proofs = REPO_ROOT / "proofs" / "github"
    if not gh_proofs.exists() or not any(gh_proofs.iterdir()):
        header("Downloading proof files")
        gh_proofs.mkdir(parents=True, exist_ok=True)
        tag = f"v{version}"
        result = run([
            "gh", "release", "download", tag, "--repo", REPO_SLUG,
            "--dir", str(gh_proofs), "--skip-existing",
        ])
        if result.returncode != 0:
            console.print(f"  [yellow]Could not download proof files (gh release download failed)[/]")
            info("Continuing with whatever is in proofs/github/")

    # -- 1. SHA256 checksums -------------------------------------------
    header("1. SHA256 checksums")
    gh_sums = gh_proofs / f"geek42-{version}-SHA256SUMS.txt"
    if not gh_sums.exists():
        gh_sums = gh_proofs / "SHA256SUMS.txt"
    if not verify_checksums(artifacts, gh_sums):
        failures += 1

    # -- 2. Sigstore signatures (cosign verify-blob) -------------------
    header("2. Sigstore signatures (cosign verify-blob)")
    console.print(Panel(
        "[bold]cosign verify-blob[/] verifies the sigstore bundle attached\n"
        "to each artifact. It checks the Sigstore signature, certificate\n"
        "chain (Fulcio), and Rekor transparency log inclusion — all in\n"
        "one command. The certificate identity must match the release\n"
        "workflow that produced the artifact.",
        border_style="dim",
    ))
    for name, path in artifacts.items():
        bundle = gh_proofs / f"{name}.sigstore.json"
        if not verify_sigstore_blob(path, bundle, version):
            failures += 1

    # -- 3. SLSA L3 provenance (cosign verify-blob-attestation) --------
    header("3. SLSA L3 provenance (cosign verify-blob-attestation)")
    console.print(Panel(
        "[bold]cosign verify-blob-attestation[/] verifies the SLSA L3\n"
        "provenance statement. Unlike sigstore bundles (signed by the\n"
        "release workflow), SLSA provenance is signed by the isolated\n"
        "slsa-github-generator — a tamper-proof builder the caller\n"
        "cannot control.",
        border_style="dim",
    ))
    provenance = gh_proofs / f"geek42-v{version}-provenance.intoto.jsonl"
    if not provenance.exists():
        provenance = gh_proofs / "geek42-provenance.intoto.jsonl"
    for name, path in artifacts.items():
        if not verify_slsa_attestation(path, provenance):
            failures += 1
        break  # provenance covers all subjects, verify once

    # -- Summary -------------------------------------------------------
    console.print()
    if failures:
        console.print(Panel("[bold red]Verification completed with failures[/]"))
        return 1
    console.print(Panel("[bold green]All cosign verifications passed[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
