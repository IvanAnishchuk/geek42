"""Verify local distribution files using Python libraries.

Uses sigstore and pypi-attestations for cryptographic verification.
Requires gh CLI only for downloading proof files (if not already
present in proofs/github/).

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
    uv run python scripts/verify_pure.py [VERSION]
    uv run python scripts/verify_pure.py 0.4.2a7
    uv run python scripts/verify_pure.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import base64
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
from rich.table import Table

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_EXTENSIONS = (".whl", ".tar.gz")

# Known CI providers and their OIDC issuers
KNOWN_HOSTS = {
    "github.com": "https://token.actions.githubusercontent.com",
}

# -- Trust anchors (derived from pyproject.toml) ---------------------------

_pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
PACKAGE_NAME = _pyproject["project"]["name"]
_repo_url = urllib.parse.urlparse(_pyproject["project"]["urls"]["Repository"])
_repo_host = _repo_url.hostname
if _repo_host not in KNOWN_HOSTS:
    console.print(f"[bold red]Unknown repository host: {_repo_host}[/]")
    console.print(f"[dim]Known hosts: {', '.join(KNOWN_HOSTS)}[/]")
    sys.exit(1)
REPO_SLUG = _repo_url.path.strip("/")
OIDC_ISSUER = KNOWN_HOSTS[_repo_host]

# Release conventions — update these if your project uses different values
RELEASE_WORKFLOW = "release.yml"
TAG_PREFIX = "v"  # tags are formatted as v{version}, e.g. v0.4.2a7

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


def is_dist_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in DIST_EXTENSIONS)


def collect_local(version: str) -> dict[str, Path]:
    dist_dir = REPO_ROOT / "dist"
    if not dist_dir.is_dir():
        return {}
    return {
        f.name: f for f in sorted(dist_dir.iterdir()) if is_dist_file(f.name) and version in f.name
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

    import sigstore.errors
    from sigstore.models import Bundle
    from sigstore.verify import Verifier, policy

    identity_str = f"https://github.com/{REPO_SLUG}/.github/workflows/{RELEASE_WORKFLOW}@refs/tags/{TAG_PREFIX}{version}"

    try:
        bundle = Bundle.from_json(bundle_path.read_bytes())
        verifier = Verifier.production()
        identity = policy.Identity(identity=identity_str, issuer=OIDC_ISSUER)
        verifier.verify_artifact(path.read_bytes(), bundle, identity)
    except (sigstore.errors.VerificationError, ValueError, OSError) as exc:
        artifact_hash = sha256(path)
        fail(f"sigstore verify: {path.name}")
        fail(f"  artifact: {artifact_hash}")
        fail(f"  error: {exc}")
        return False

    ok(f"sigstore verify: {path.name} ({sha256(path)})")

    try:
        from typing import cast

        from cryptography.x509 import SubjectAlternativeName, UniformResourceIdentifier
        from cryptography.x509.oid import ExtensionOID

        cert = bundle.signing_certificate
        san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san_val = cast(SubjectAlternativeName, san_ext.value)
        sans = san_val.get_values_for_type(UniformResourceIdentifier)
        if sans:
            info(f"  signed by: {sans[0]}")
        info(f"  issuer: {cert.issuer.rfc4514_string()}")
        info(f"  trust root: {OIDC_ISSUER}")
    except (ImportError, ValueError, KeyError):
        info(f"  trust root: {OIDC_ISSUER}")

    return True


# -- 3. SLSA L3 provenance ---------------------------------------------


def verify_slsa_provenance(path: Path, provenance_path: Path, version: str) -> bool:
    if not provenance_path.exists():
        info("No SLSA provenance file found")
        return True

    import sigstore.errors
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
    except (sigstore.errors.VerificationError, ValueError, OSError) as exc:
        fail(f"SLSA L3 provenance: {path.name}")
        fail(f"  {exc}")
        return False

    # verify_dsse checks the signature but NOT that the artifact matches
    # the provenance subjects. We must check that ourselves.
    artifact_hash = sha256(path)
    try:
        raw = json.loads(provenance_path.read_text())
        env = raw.get("dsseEnvelope", {})
        stmt = json.loads(base64.b64decode(env["payload"]))
        subjects = stmt.get("subject", [])
        subject_hashes = {s["digest"]["sha256"] for s in subjects}
        if artifact_hash not in subject_hashes:
            fail("SLSA L3 provenance: artifact hash not in provenance subjects")
            fail(f"  artifact: {artifact_hash}")
            fail(f"  subjects: {subject_hashes}")
            return False
    except (KeyError, json.JSONDecodeError) as exc:
        fail(f"SLSA L3 provenance: could not verify subject match: {exc}")
        return False

    ok(f"SLSA L3 provenance verified: {path.name} ({artifact_hash})")
    info("  signed by: slsa-framework/slsa-github-generator@v2.1.0")
    info(f"  trust root: {OIDC_ISSUER}")

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
                show_header=False,
                padding=(0, 2),
                expand=True,
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
    except (KeyError, json.JSONDecodeError) as exc:
        info(f"  (could not display provenance details: {exc})")

    return True


# -- 4. PyPI attestations (PEP 740) ------------------------------------


def verify_pypi_attestation(path: Path, provenance: dict, index_name: str) -> bool:
    from pypi_attestations import Attestation, AttestationError, GitHubPublisher
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
            artifact_hash = sha256(path)
            try:
                predicate_type, _ = att.verify(publisher, dist)
                repo = publisher_data.get("repository", "?")
                wf = publisher_data.get("workflow", "?")
                ok(f"{index_name}: {path.name} ({artifact_hash})")
                info(f"  signed by: {repo}/{wf}")
                info(f"  environment: {publisher_data.get('environment', '?')}")
                info(f"  trust root: {OIDC_ISSUER}")
            except (AttestationError, ValueError) as exc:
                fail(f"{index_name}: {path.name}")
                fail(f"  artifact: {artifact_hash}")
                fail(f"  error: {exc}")
                all_ok = False
                continue

            table = Table(
                title=f"{index_name} PEP 740 (verified)",
                show_header=False,
                padding=(0, 2),
                expand=True,
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
    console.print(
        Panel(
            f"Verifying [bold]{PACKAGE_NAME} {version}[/] with Python libraries\n"
            f"[dim]Uses sigstore + pypi-attestations; gh needed for proof download[/]"
        )
    )

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
        tag = f"v{version}"
        gh = shutil.which("gh") or "gh"
        subprocess.run(  # noqa: S603 — args are list literals, no shell
            [
                gh,
                "release",
                "download",
                tag,
                "--repo",
                REPO_SLUG,
                "--dir",
                str(gh_proofs),
                "--skip-existing",
            ],
            capture_output=True,
            text=True,
            check=False,
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
    for _name, path in artifacts.items():
        if not verify_slsa_provenance(path, provenance, version):
            failures += 1
        break  # verify once

    # -- 4. GitHub attestations (sigstore Python) -----------------------
    import sigstore.errors

    header("4. GitHub attestations (Python sigstore library)")
    for name, path in artifacts.items():
        att_file = gh_proofs / f"{name}.gh-attestation.json"
        if not att_file.exists():
            info(f"No GH attestation file for {name}")
            continue
        try:
            data = json.loads(att_file.read_text())
            if not isinstance(data, list) or not data:
                info(f"Empty GH attestation for {name}")
                continue
            bundle_json = json.dumps(data[0]["attestation"]["bundle"]).encode()

            from sigstore.models import Bundle
            from sigstore.verify import Verifier, policy

            bundle = Bundle.from_json(bundle_json)
            verifier = Verifier.production()
            identity = policy.Identity(
                identity=(
                    f"https://github.com/{REPO_SLUG}"
                    f"/.github/workflows/{RELEASE_WORKFLOW}@refs/tags/{TAG_PREFIX}{version}"
                ),
                issuer=OIDC_ISSUER,
            )
            verifier.verify_dsse(bundle, identity)

            # verify_dsse checks signature but NOT artifact digest match
            artifact_hash = sha256(path)
            att_bundle = data[0]["attestation"]["bundle"]
            dsse = att_bundle.get("dsseEnvelope", {})
            stmt = json.loads(base64.b64decode(dsse["payload"]))
            subject_hashes = {s["digest"]["sha256"] for s in stmt.get("subject", [])}
            if artifact_hash not in subject_hashes:
                fail(f"GH attestation: {name}")
                fail(f"  artifact: {artifact_hash}")
                fail(f"  expected: {subject_hashes}")
                failures += 1
                continue

            ok(f"GH attestation verified: {name} ({artifact_hash})")
            info(f"  signed by: {RELEASE_WORKFLOW}@refs/tags/{TAG_PREFIX}{version}")
            info(f"  trust root: {OIDC_ISSUER}")
        except (
            sigstore.errors.VerificationError,
            KeyError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            fail(f"GH attestation: {name} — {exc}")
            failures += 1

    # -- 5. PyPI / TestPyPI attestations (PEP 740) ---------------------
    header("5. PyPI / TestPyPI attestations (pypi-attestations library)")
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
            if not verify_pypi_attestation(path, prov, index_name):
                failures += 1

    # -- Summary -------------------------------------------------------
    console.print()
    if failures:
        console.print(Panel("[bold red]Verification completed with failures[/]"))
        return 1
    console.print(Panel("[bold green]All pure-Python verifications passed[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
