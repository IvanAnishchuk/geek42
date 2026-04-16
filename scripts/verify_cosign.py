"""Verify local distribution files using cosign.

Verifies files in dist/ against all five proof providers using cosign
for cryptographic verification. Also requires gh CLI for downloading
proof files (if not already present in proofs/github/).

GitHub attestations and PyPI PEP 740 attestations contain standard
sigstore bundles inside wrapper formats; this script extracts them
for cosign verification.

1. SHA256 checksums       — manual comparison
2. Sigstore signatures    — cosign verify-blob
3. GitHub attestations    — cosign verify-blob-attestation (extracted bundle)
4. SLSA L3 provenance     — cosign verify-blob-attestation
5. PyPI attestations      — cosign verify-blob-attestation (restructured bundle)

Requirements:
  - cosign  (Go binary from sigstore)
  - gh      (GitHub CLI, only for downloading proof files)

Usage:
    uv run python scripts/verify_cosign.py [VERSION]
    uv run python scripts/verify_cosign.py 0.4.2a7
    uv run python scripts/verify_cosign.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
import urllib.parse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_EXTENSIONS = (".whl", ".tar.gz")

# Known CI providers and their OIDC issuers
KNOWN_HOSTS = {
    "github.com": "https://token.actions.githubusercontent.com",
}

# -- Trust anchors (derived from pyproject.toml) ---------------------------

try:
    _pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    PACKAGE_NAME = _pyproject["project"]["name"]
    _repo_url = urllib.parse.urlparse(_pyproject["project"]["urls"]["Repository"])
    _repo_host = _repo_url.hostname
except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError) as exc:
    console.print(f"[bold red]Cannot derive trust anchors from pyproject.toml: {exc}[/]")
    console.print(
        "[dim]Ensure pyproject.toml exists with [project].name and [project.urls].Repository[/]"
    )
    sys.exit(1)
if _repo_host not in KNOWN_HOSTS:
    console.print(f"[bold red]Unknown repository host: {_repo_host}[/]")
    console.print(f"[dim]Known hosts: {', '.join(KNOWN_HOSTS)}[/]")
    sys.exit(1)
REPO_SLUG = _repo_url.path.strip("/")
OIDC_ISSUER = KNOWN_HOSTS[_repo_host]

# Release conventions — update these if your project uses different values
RELEASE_WORKFLOW = "release.yml"
TAG_PREFIX = "v"  # tags are formatted as v{version}, e.g. v0.4.2a7
# OIDC identity template — {version} is substituted at verification time
IDENTITY_TEMPLATE = (
    f"https://github.com/{REPO_SLUG}"
    f"/.github/workflows/{RELEASE_WORKFLOW}@refs/tags/{TAG_PREFIX}{{version}}"
)

PYPI_INDEX_DIRS = ["pypi", "testpypi"]


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
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 — args are list literals, no shell


def is_dist_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in DIST_EXTENSIONS)


def collect_local(version: str) -> dict[str, Path]:
    dist_dir = REPO_ROOT / "dist"
    if not dist_dir.is_dir():
        return {}
    return {
        f.name: f for f in sorted(dist_dir.iterdir()) if is_dist_file(f.name) and version in f.name
    }


def _extract_san_from_bundle(bundle_path: Path) -> str | None:
    """Extract the SAN URI from a sigstore bundle's signing certificate."""
    try:
        bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
        cert_b64 = (
            bundle_data.get("verificationMaterial", {}).get("certificate", {}).get("rawBytes", "")
        )
        if not cert_b64:
            return None
        cert_pem = "-----BEGIN CERTIFICATE-----\n" + cert_b64 + "\n-----END CERTIFICATE-----\n"
        openssl = shutil.which("openssl")
        if not openssl:
            return None
        result = subprocess.run(  # noqa: S603 — args are list literals, no shell
            [openssl, "x509", "-noout", "-ext", "subjectAltName"],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("URI:"):
                return stripped.removeprefix("URI:")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _verify_bundle_identity(bundle_path: Path, expected_identity: str, label: str) -> bool:
    """Extract SAN from bundle and compare against expected identity. Returns False on failure."""
    san = _extract_san_from_bundle(bundle_path)
    if not san:
        fail(f"{label}: could not extract SAN from bundle certificate")
        return False
    if san != expected_identity:
        fail(f"{label}: identity mismatch")
        fail(f"  certificate SAN: {san}")
        fail(f"  expected: {expected_identity}")
        return False
    return True


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

    # Extract and verify identity from bundle certificate before cosign check
    identity = IDENTITY_TEMPLATE.format(version=version)
    if not _verify_bundle_identity(bundle, identity, f"cosign verify-blob: {path.name}"):
        return False

    result = run(
        [
            "cosign",
            "verify-blob",
            "--certificate-oidc-issuer",
            OIDC_ISSUER,
            "--certificate-identity",
            identity,
            "--bundle",
            str(bundle),
            str(path),
        ]
    )

    artifact_hash = sha256(path)
    if result.returncode != 0:
        fail(f"cosign verify-blob: {path.name}")
        fail(f"  artifact: {artifact_hash}")
        if stderr := result.stderr.strip():
            fail(f"  error: {stderr.splitlines()[-1]}")
        return False

    ok(f"cosign verify-blob: {path.name} ({artifact_hash})")
    info(f"  signed by: {identity}")
    info(f"  trust root: {OIDC_ISSUER}")
    return True


def verify_slsa_attestation(path: Path, provenance: Path) -> bool:
    """Verify SLSA L3 provenance using cosign verify-blob-attestation."""
    if not provenance.exists():
        info("No SLSA provenance file found")
        return True  # not a failure, just not available

    # SLSA provenance is signed by the slsa-framework generator, not our workflow
    result = run(
        [
            "cosign",
            "verify-blob-attestation",
            "--certificate-oidc-issuer",
            OIDC_ISSUER,
            "--certificate-identity-regexp",
            "https://github.com/slsa-framework/slsa-github-generator/",
            "--type",
            "slsaprovenance",
            "--bundle",
            str(provenance),
            str(path),
        ]
    )
    artifact_hash = sha256(path)
    if result.returncode != 0:
        fail(f"cosign SLSA L3: {path.name}")
        fail(f"  artifact: {artifact_hash}")
        if stderr := result.stderr.strip():
            fail(f"  error: {stderr.splitlines()[-1]}")
        return False

    ok(f"cosign SLSA L3: {path.name} ({artifact_hash})")
    info("  signed by: slsa-framework/slsa-github-generator")
    info(f"  trust root: {OIDC_ISSUER}")
    return True


def verify_gh_attestation(path: Path, gh_proofs: Path, version: str) -> bool:
    """Verify GitHub attestation using pre-extracted or inline-extracted bundle."""
    bundle_file = gh_proofs / f"{path.name}.gh-attestation-bundle.json"

    # If pre-extracted bundle doesn't exist, try extracting from attestation JSON
    if not bundle_file.exists():
        att_file = gh_proofs / f"{path.name}.gh-attestation.json"
        if not att_file.exists():
            info(f"No GH attestation file for {path.name}")
            return True
        try:
            data = json.loads(att_file.read_text())
            if not isinstance(data, list) or not data:
                info(f"Empty or invalid GH attestation for {path.name}")
                return True
            bundle_json = json.dumps(data[0]["attestation"]["bundle"])
            bundle_file.write_text(bundle_json)
        except (json.JSONDecodeError, KeyError) as exc:
            fail(f"Could not parse GH attestation: {exc}")
            return False

    identity = IDENTITY_TEMPLATE.format(version=version)
    if not _verify_bundle_identity(bundle_file, identity, f"cosign GH attestation: {path.name}"):
        return False

    result = run(
        [
            "cosign",
            "verify-blob-attestation",
            "--certificate-oidc-issuer",
            OIDC_ISSUER,
            "--certificate-identity",
            identity,
            "--type",
            "slsaprovenance",
            "--bundle",
            str(bundle_file),
            str(path),
        ]
    )
    artifact_hash = sha256(path)
    if result.returncode != 0:
        fail(f"cosign GH attestation: {path.name}")
        fail(f"  artifact: {artifact_hash}")
        if stderr := result.stderr.strip():
            fail(f"  error: {stderr.splitlines()[-1]}")
        return False

    ok(f"cosign GH attestation: {path.name} ({artifact_hash})")
    info(f"  signed by: {identity}")
    info(f"  trust root: {OIDC_ISSUER}")
    return True


def _restructure_pep740_to_cosign(att: dict) -> dict:
    """Restructure a PEP 740 attestation into a cosign-compatible sigstore bundle.

    Required PEP 740 keys: verification_material.{certificate, transparency_entries},
    envelope.{statement, signature}. KeyError on missing keys is intentional —
    malformed attestations should fail loudly.
    """
    vm = att.get("verification_material", {})
    return {
        "mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json",
        "verificationMaterial": {
            "certificate": {"rawBytes": vm["certificate"]},
            "tlogEntries": vm["transparency_entries"],
            "timestampVerificationData": {},
        },
        "dsseEnvelope": {
            "payload": att["envelope"]["statement"],
            "payloadType": "application/vnd.in-toto+json",
            "signatures": [{"sig": att["envelope"]["signature"]}],
        },
    }


def verify_pypi_attestation(
    path: Path,
    provenance: dict,
    index_name: str,
    version: str,
) -> bool:
    """Verify PyPI PEP 740 attestation using cosign + pypi-attestations inspect."""
    index_dir = "testpypi" if index_name == "TestPyPI" else "pypi"
    proofs_dir = REPO_ROOT / "proofs" / index_dir
    proofs_dir.mkdir(parents=True, exist_ok=True)

    bundles = provenance.get("attestation_bundles", [])
    if not bundles:
        fail(f"No attestation bundles in {index_name} provenance")
        return False

    all_ok = True
    for bundle_data in bundles:
        publisher = bundle_data.get("publisher", {})

        for att in bundle_data.get("attestations", []):
            # Use pre-extracted cosign bundle or restructure inline
            bundle_file = proofs_dir / f"{path.name}.cosign-bundle.json"
            if not bundle_file.exists():
                cosign_bundle = _restructure_pep740_to_cosign(att)
                bundle_file.write_text(json.dumps(cosign_bundle, indent=2))

            # Also extract .publish.attestation for inspect
            att_file = proofs_dir / f"{path.name}.publish.attestation"
            if not att_file.exists():
                att_file.write_text(json.dumps(att))

            identity = IDENTITY_TEMPLATE.format(version=version)
            if not _verify_bundle_identity(
                bundle_file, identity, f"cosign {index_name} PEP 740: {path.name}"
            ):
                all_ok = False
                continue

            result = run(
                [
                    "cosign",
                    "verify-blob-attestation",
                    "--certificate-oidc-issuer",
                    OIDC_ISSUER,
                    "--certificate-identity",
                    identity,
                    "--type",
                    "https://docs.pypi.org/attestations/publish/v1",
                    "--bundle",
                    str(bundle_file),
                    str(path),
                ]
            )
            artifact_hash = sha256(path)
            if result.returncode != 0:
                fail(f"cosign {index_name} PEP 740: {path.name}")
                fail(f"  artifact: {artifact_hash}")
                if stderr := result.stderr.strip():
                    fail(f"  error: {stderr.splitlines()[-1]}")
                all_ok = False
            else:
                repo = publisher.get("repository", "?")
                wf = publisher.get("workflow", "?")
                ok(f"cosign {index_name} PEP 740: {path.name} ({artifact_hash})")
                info(f"  signed by: {repo}/{wf}")
                info(f"  environment: {publisher.get('environment', '?')}")
                info(f"  trust root: {OIDC_ISSUER}")

                # Show PEP 740 details with pypi-attestations inspect
                inspect_result = run(
                    [
                        "uv",
                        "run",
                        "pypi-attestations",
                        "inspect",
                        str(att_file),
                    ]
                )
                # inspect writes to stderr (uses rich console internally)
                inspect_output = inspect_result.stderr or inspect_result.stdout
                if inspect_result.returncode == 0 and inspect_output:
                    for line in inspect_output.strip().splitlines():
                        info(line)

    return all_ok


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
    console.print(
        Panel(
            f"Verifying [bold]{PACKAGE_NAME} {version}[/] with cosign\n"
            f"[dim]Uses cosign for verification; gh needed for proof download[/]"
        )
    )

    # Check cosign is available
    result = run(["cosign", "version"])
    if result.returncode != 0:
        console.print(
            Panel(
                "[bold red]cosign not found. Install from https://docs.sigstore.dev/cosign/system_config/installation/[/]"
            )
        )
        return 1

    failures = 0

    # -- Locate artifacts in dist/ -------------------------------------
    header("Distribution files")
    artifacts = collect_local(version)
    if not artifacts:
        console.print(
            Panel(
                f"[bold red]No files matching version {version} found in dist/[/]\n"
                "Download with: uv run python scripts/download_release.py " + version,
            )
        )
        return 1
    console.print(f"  Verifying {len(artifacts)} file(s) from dist/:")
    for name, path in artifacts.items():
        info(f"{name}: {sha256(path)}")

    # -- Ensure proof files exist --------------------------------------
    gh_proofs = REPO_ROOT / "proofs" / "github"
    if not gh_proofs.exists() or not any(gh_proofs.iterdir()):
        header("Downloading proof files")
        gh_proofs.mkdir(parents=True, exist_ok=True)
        tag = f"{TAG_PREFIX}{version}"
        result = run(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                REPO_SLUG,
                "--dir",
                str(gh_proofs),
                "--skip-existing",
            ]
        )
        if result.returncode != 0:
            console.print(
                "  [yellow]Could not download proof files (gh release download failed)[/]"
            )
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
    console.print(
        Panel(
            "[bold]cosign verify-blob[/] verifies the sigstore bundle attached\n"
            "to each artifact. It checks the Sigstore signature, certificate\n"
            "chain (Fulcio), and Rekor transparency log inclusion — all in\n"
            "one command. The certificate identity must match the release\n"
            "workflow that produced the artifact.",
            border_style="dim",
        )
    )
    for name, path in artifacts.items():
        bundle = gh_proofs / f"{name}.sigstore.json"
        if not verify_sigstore_blob(path, bundle, version):
            failures += 1

    # -- 3. SLSA L3 provenance (cosign verify-blob-attestation) --------
    header("3. SLSA L3 provenance (cosign verify-blob-attestation)")
    console.print(
        Panel(
            "[bold]cosign verify-blob-attestation[/] verifies the SLSA L3\n"
            "provenance statement. Unlike sigstore bundles (signed by the\n"
            "release workflow), SLSA provenance is signed by the isolated\n"
            "slsa-github-generator — a tamper-proof builder the caller\n"
            "cannot control.",
            border_style="dim",
        )
    )
    provenance = gh_proofs / f"geek42-v{version}-provenance.intoto.jsonl"
    if not provenance.exists():
        provenance = gh_proofs / "geek42-provenance.intoto.jsonl"
    for _name, path in artifacts.items():
        if not verify_slsa_attestation(path, provenance):
            failures += 1
        break  # provenance covers all subjects, verify once

    # -- 4. GitHub attestations (cosign verify-blob-attestation) --------
    header("4. GitHub attestations (cosign verify-blob-attestation)")
    console.print(
        Panel(
            "[bold]GitHub attestations[/] contain standard sigstore DSSE\n"
            "bundles. This script extracts the bundle from the gh attestation\n"
            "JSON wrapper and verifies it with cosign.",
            border_style="dim",
        )
    )
    for _name, path in artifacts.items():
        if not verify_gh_attestation(path, gh_proofs, version):
            failures += 1

    # -- 5. PyPI / TestPyPI attestations (cosign) ----------------------
    header("5. PyPI / TestPyPI attestations (cosign)")
    console.print(
        Panel(
            "[bold]PyPI PEP 740 attestations[/] use a different JSON format\n"
            "but contain the same sigstore primitives (certificate + Rekor\n"
            "entry + DSSE envelope). Uses pre-extracted cosign bundles from\n"
            "download_release.py, or restructures inline as fallback.\n"
            "Attestation details shown via pypi-attestations inspect.",
            border_style="dim",
        )
    )
    for index_dir in PYPI_INDEX_DIRS:
        index_name = "TestPyPI" if index_dir == "testpypi" else "PyPI"
        if index_dir == "testpypi":
            console.print(
                Panel(
                    "[bold yellow]WARNING: TestPyPI is NOT a production index.[/]",
                    border_style="yellow",
                )
            )
        proofs_dir = REPO_ROOT / "proofs" / index_dir
        if not proofs_dir.is_dir():
            fail(f"{index_name}: no proofs directory (run download_release.py first)")
            failures += 1
            continue
        for name, path in artifacts.items():
            prov_file = proofs_dir / f"{name}.provenance.json"
            if not prov_file.exists():
                info(f"{index_name}: no attestation for {name}")
                continue
            try:
                prov = json.loads(prov_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                fail(f"{index_name}: invalid provenance for {name}: {exc}")
                failures += 1
                continue
            if not verify_pypi_attestation(path, prov, index_name, version):
                failures += 1

    # -- Summary -------------------------------------------------------
    console.print()
    if failures:
        console.print(Panel("[bold red]Verification completed with failures[/]"))
        return 1
    console.print(Panel("[bold green]All cosign verifications passed[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
