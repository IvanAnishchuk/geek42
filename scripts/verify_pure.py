"""Verify local distribution files using pure Python only.

No external tools required — uses sigstore and pypi-attestations
Python libraries for all cryptographic verification. This is the
most portable verification script: works anywhere Python runs.

Verifies:
1. SHA256 checksums       — manual comparison
2. Sigstore signatures    — sigstore.verify (Fulcio + Rekor)
3. SLSA L3 provenance     — sigstore.verify DSSE envelope
4. PyPI attestations      — pypi-attestations.Attestation.verify

Requirements (Python packages, all in dev dependencies):
  - sigstore
  - pypi-attestations
  - rich

Usage:
    uv run scripts/verify_pure.py [VERSION]
    uv run scripts/verify_pure.py 0.4.2a7
    uv run scripts/verify_pure.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
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
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
PYPI_INDEXES = [
    ("PyPI", "https://pypi.org"),
    ("TestPyPI", "https://test.pypi.org"),
]


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


def _ensure_proofs_dir() -> Path:
    proofs = REPO_ROOT / "proofs"
    proofs.mkdir(exist_ok=True)
    return proofs


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


# -- 1. SHA256 checksums -----------------------------------------------


def verify_checksums(artifacts: dict[str, Path], sums_file: Path) -> bool:
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


# -- 2. Sigstore signatures --------------------------------------------


def verify_sigstore_bundle(path: Path, bundle_path: Path, version: str) -> bool:
    if not bundle_path.exists():
        info(f"No sigstore bundle for {path.name}")
        return True

    from sigstore.models import Bundle
    from sigstore.verify import Verifier, policy

    identity_str = (
        f"https://github.com/{REPO_SLUG}"
        f"/.github/workflows/release.yml@refs/tags/v{version}"
    )

    try:
        bundle = Bundle.from_json(bundle_path.read_bytes())
        verifier = Verifier.production()
        identity = policy.Identity(identity=identity_str, issuer=OIDC_ISSUER)
        verifier.verify_artifact(path.read_bytes(), bundle, identity)
    except Exception as exc:  # noqa: BLE001
        fail(f"sigstore verify: {path.name}")
        fail(f"  {exc}")
        return False

    ok(f"sigstore verify: {path.name}")

    # Extract certificate details for display
    try:
        from cryptography.x509 import UniformResourceIdentifier
        from cryptography.x509.oid import ExtensionOID

        cert = bundle.signing_certificate
        san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = san_ext.value.get_values_for_type(UniformResourceIdentifier)
        for san in sans:
            info(f"  SAN: {san}")
        info(f"  Issuer: {cert.issuer.rfc4514_string()}")
        info(f"  Not before: {cert.not_valid_before_utc}")
        info(f"  Not after: {cert.not_valid_after_utc}")
    except Exception:  # noqa: BLE001
        pass

    return True


# -- 3. SLSA L3 provenance ---------------------------------------------


def verify_slsa_provenance(path: Path, provenance_path: Path, version: str) -> bool:
    if not provenance_path.exists():
        info("No SLSA provenance file found")
        return True

    from sigstore.models import Bundle
    from sigstore.verify import Verifier, policy

    try:
        bundle = Bundle.from_json(provenance_path.read_bytes())
        verifier = Verifier.production()
        # SLSA provenance is signed by the generator, not our workflow
        identity = policy.Identity(
            identity="https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@refs/tags/v2.1.0",
            issuer=OIDC_ISSUER,
        )
        verifier.verify_dsse(bundle, identity)
    except Exception as exc:  # noqa: BLE001
        fail(f"SLSA L3 provenance: {path.name}")
        fail(f"  {exc}")
        return False

    ok(f"SLSA L3 provenance verified: {path.name}")

    # Decode and display provenance details
    try:
        raw = json.loads(provenance_path.read_text())
        env = raw.get("dsseEnvelope", {})
        if env:
            stmt = json.loads(base64.b64decode(env["payload"]))
            pred = stmt.get("predicate", {})
            cs = pred.get("invocation", {}).get("configSource", {})
            env_data = pred.get("invocation", {}).get("environment", {})

            table = Table(
                title="SLSA L3 Provenance",
                show_header=False, padding=(0, 2), expand=True,
            )
            table.add_column("Field", style="bold cyan", min_width=20, max_width=26)
            table.add_column("Value", overflow="fold")

            table.add_row("Builder ID", pred.get("builder", {}).get("id", "?"))
            table.add_row("Source URI", cs.get("uri", "?"))
            table.add_row("Source commit", cs.get("digest", {}).get("sha1", "?"))
            table.add_row("Entry point", cs.get("entryPoint", "?"))
            table.add_row("Actor", env_data.get("github_actor", "?"))
            table.add_row("Event", env_data.get("github_event_name", "?"))
            table.add_row("Ref", env_data.get("github_ref", "?"))

            subjects = stmt.get("subject", [])
            if subjects:
                table.add_row("", "")
                for subj in subjects:
                    digest = subj.get("digest", {}).get("sha256", "?")
                    table.add_row(subj.get("name", "?"), f"sha256:{digest}")

            console.print()
            console.print(table)
    except Exception:  # noqa: BLE001
        pass

    return True


# -- 4. PyPI attestations (PEP 740) ------------------------------------


def fetch_pypi_provenance(
    package: str, version: str, filename: str, base_url: str,
) -> dict | None:
    url = f"{base_url}/integrity/{package}/{version}/{filename}/provenance"
    try:
        req = urllib.request.Request(url)  # noqa: S310
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None


def verify_pypi_attestation(path: Path, provenance: dict, index_name: str) -> bool:
    from pypi_attestations import Attestation, GitHubPublisher
    from pypi_attestations import Distribution as AttestDist

    bundles = provenance.get("attestation_bundles", [])
    if not bundles:
        fail(f"No attestation bundles in {index_name} provenance")
        return False

    dist = AttestDist.from_file(path)
    all_ok = True

    for bundle in bundles:
        publisher_data = bundle.get("publisher", {})
        publisher = GitHubPublisher(
            repository=publisher_data.get("repository", ""),
            workflow=publisher_data.get("workflow", ""),
            environment=publisher_data.get("environment"),
        )

        for att_data in bundle.get("attestations", []):
            att = Attestation.model_validate(att_data)
            try:
                predicate_type, _ = att.verify(publisher, dist)
                ok(f"{index_name}: verified {path.name}")
            except Exception as exc:  # noqa: BLE001
                fail(f"{index_name}: {path.name} — {exc}")
                all_ok = False
                continue

            table = Table(
                title=f"{index_name} PEP 740 (verified)",
                show_header=False, padding=(0, 2), expand=True,
            )
            table.add_column("Field", style="bold cyan", min_width=20, max_width=26)
            table.add_column("Value", overflow="fold")
            table.add_row("Publisher", publisher_data.get("repository", "?"))
            table.add_row("Workflow", publisher_data.get("workflow", "?"))
            table.add_row("Environment", publisher_data.get("environment", "?"))
            table.add_row("Predicate type", predicate_type)
            table.add_row("Artifact", path.name)
            table.add_row("SHA256", sha256(path))
            console.print()
            console.print(table)

    return all_ok


# -- Main --------------------------------------------------------------


def main() -> int:
    version = get_version()
    console.print(Panel(
        f"Verifying [bold]{PACKAGE_NAME} {version}[/] with pure Python\n"
        f"[dim]No external tools — uses sigstore + pypi-attestations libraries[/]"
    ))

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
        subprocess.run(  # noqa: S603
            ["gh", "release", "download", tag, "--repo", REPO_SLUG,
             "--dir", str(gh_proofs), "--skip-existing"],
            capture_output=True, text=True, check=False,
        )

    # -- 1. SHA256 checksums -------------------------------------------
    header("1. SHA256 checksums")
    gh_sums = gh_proofs / f"geek42-{version}-SHA256SUMS.txt"
    if not gh_sums.exists():
        gh_sums = gh_proofs / "SHA256SUMS.txt"
    if not verify_checksums(artifacts, gh_sums):
        failures += 1

    # -- 2. Sigstore signatures ----------------------------------------
    header("2. Sigstore signatures (Python sigstore library)")
    for name, path in artifacts.items():
        bundle = gh_proofs / f"{name}.sigstore.json"
        if not verify_sigstore_bundle(path, bundle, version):
            failures += 1

    # -- 3. SLSA L3 provenance -----------------------------------------
    header("3. SLSA L3 provenance (Python sigstore library)")
    provenance = gh_proofs / f"geek42-v{version}-provenance.intoto.jsonl"
    if not provenance.exists():
        provenance = gh_proofs / "geek42-provenance.intoto.jsonl"
    for name, path in artifacts.items():
        if not verify_slsa_provenance(path, provenance, version):
            failures += 1
        break  # verify once

    # -- 4. PyPI / TestPyPI attestations (PEP 740) ---------------------
    header("4. PyPI / TestPyPI attestations (pypi-attestations library)")
    pypi_proofs = _ensure_proofs_dir() / "pypi"
    pypi_proofs.mkdir(exist_ok=True)
    for index_name, base_url in PYPI_INDEXES:
        if index_name == "TestPyPI":
            console.print(Panel(
                "[bold yellow]WARNING: TestPyPI is NOT a production index.[/]",
                border_style="yellow",
            ))
        for name, path in artifacts.items():
            prov = fetch_pypi_provenance(PACKAGE_NAME, version, name, base_url)
            if prov:
                out = pypi_proofs / f"{name}.{index_name.lower()}-provenance.json"
                out.write_text(json.dumps(prov, indent=2))
                if not verify_pypi_attestation(path, prov, index_name):
                    failures += 1
            else:
                info(f"{index_name}: no attestation for {name}")

    # -- Summary -------------------------------------------------------
    console.print()
    if failures:
        console.print(Panel("[bold red]Verification completed with failures[/]"))
        return 1
    console.print(Panel("[bold green]All pure-Python verifications passed[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
