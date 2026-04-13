"""Download a geek42 release and all proof artifacts.

Downloads from three sources:
1. GitHub Release — wheel, sdist, sigstore bundles, SBOM, checksums,
   SLSA provenance → dist/ and proofs/github/
2. GitHub Attestation API — build attestations → proofs/github/
3. PyPI / TestPyPI Integrity API — PEP 740 provenance → proofs/pypi/

Extracted proof files ready for all three verify scripts:
- *.publish.attestation  — for pypi-attestations CLI (verify_provenance.py)
- *.cosign-bundle.json   — for cosign (verify_cosign.py)
- *.gh-attestation-bundle.json — for cosign (verify_cosign.py)

Usage:
    uv run python scripts/download_release.py [VERSION]
    uv run python scripts/download_release.py 0.4.2a7
    uv run python scripts/download_release.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
    print(f"Error: Unknown repository host: {_repo_host}")
    print(f"Known hosts: {', '.join(KNOWN_HOSTS)}")
    sys.exit(1)
REPO_SLUG = _repo_url.path.strip("/")

# Release conventions — update these if your project uses different values
TAG_PREFIX = "v"  # tags are formatted as v{version}, e.g. v0.4.2a7

DIST_DIR = REPO_ROOT / "dist"
PROOFS_DIR = REPO_ROOT / "proofs" / "github"

PYPI_INDEXES = [
    ("pypi", "https://pypi.org"),
    ("testpypi", "https://test.pypi.org"),
]


def get_version() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].removeprefix("v")
    init = REPO_ROOT / "src" / "geek42" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    print("Could not detect version. Pass it as an argument.")
    sys.exit(1)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 — args are list literals, no shell


def is_dist_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in DIST_EXTENSIONS)


# -- GitHub Release --------------------------------------------------------


def download_github_release(version: str) -> bool:
    """Download all assets from a GitHub Release."""
    tag = f"{TAG_PREFIX}{version}"
    gh = shutil.which("gh") or "gh"
    result = run(
        [
            gh,
            "release",
            "download",
            tag,
            "--repo",
            REPO_SLUG,
            "--dir",
            str(DIST_DIR),
            "--skip-existing",
        ]
    )
    if result.returncode != 0:
        print(f"Error: GitHub Release {tag} not found")
        if result.stderr:
            print(f"  {result.stderr.strip()}")
        return False

    # Move non-distribution files to proofs/github/
    for f in sorted(DIST_DIR.iterdir()):
        if not is_dist_file(f.name):
            target = PROOFS_DIR / f.name
            if not target.exists():
                f.rename(target)
            else:
                f.unlink()  # duplicate, already in proofs
    return True


# -- GitHub Attestations ---------------------------------------------------


def fetch_gh_attestations(version: str) -> None:
    """Fetch and extract GitHub attestation bundles for each dist file."""
    gh = shutil.which("gh") or "gh"
    for f in sorted(DIST_DIR.iterdir()):
        if not is_dist_file(f.name):
            continue
        att_file = PROOFS_DIR / f"{f.name}.gh-attestation.json"
        if att_file.exists():
            continue

        result = run(
            [
                gh,
                "attestation",
                "verify",
                str(f),
                "--repo",
                REPO_SLUG,
                "--format",
                "json",
            ]
        )
        if result.returncode != 0:
            print(f"  gh attestation: {f.name} — not available")
            continue

        try:
            records = json.loads(result.stdout)
            if isinstance(records, list) and records:
                att_file.write_text(json.dumps(records, indent=2))
                print(f"  gh attestation: {f.name} — saved")

                # Extract inner sigstore bundle for cosign
                bundle_json = json.dumps(records[0]["attestation"]["bundle"])
                bundle_file = PROOFS_DIR / f"{f.name}.gh-attestation-bundle.json"
                bundle_file.write_text(bundle_json)
                print(f"  gh attestation bundle: {f.name} — extracted")
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"  gh attestation: {f.name} — parse error: {exc}")


# -- PyPI / TestPyPI Provenance --------------------------------------------


def fetch_pypi_provenance(
    package: str,
    version: str,
    filename: str,
    base_url: str,
) -> dict | None:
    """Fetch provenance from PyPI Integrity API."""
    url = f"{base_url}/integrity/{package}/{version}/{filename}/provenance"
    if not url.startswith(("https://pypi.org/", "https://test.pypi.org/")):
        return None
    try:
        req = urllib.request.Request(url)  # noqa: S310 — URL validated above
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None  # no attestation available — expected
        print(f"  Warning: HTTP {exc.code} from {url}")
        raise
    except urllib.error.URLError as exc:
        print(f"  Warning: network error fetching {url}: {exc.reason}")
        raise
    except json.JSONDecodeError:
        print(f"  Warning: invalid JSON from {url}")
        raise


def extract_pypi_proofs(version: str) -> None:
    """Fetch PyPI/TestPyPI provenance and extract all proof formats.

    Each index gets its own directory: proofs/pypi/, proofs/testpypi/.
    """
    for index_name, base_url in PYPI_INDEXES:
        proofs_dir = REPO_ROOT / "proofs" / index_name
        proofs_dir.mkdir(parents=True, exist_ok=True)

        for f in sorted(DIST_DIR.iterdir()):
            if not is_dist_file(f.name):
                continue

            try:
                prov = fetch_pypi_provenance(PACKAGE_NAME, version, f.name, base_url)
            except (urllib.error.URLError, json.JSONDecodeError) as exc:
                print(f"  {index_name}: {f.name} — fetch failed: {exc}")
                continue
            if not prov:
                print(f"  {index_name}: {f.name} — no attestation")
                continue

            # Save raw provenance
            prov_file = proofs_dir / f"{f.name}.provenance.json"
            prov_file.write_text(json.dumps(prov, indent=2))
            print(f"  {index_name}: {f.name} — provenance saved")

            bundles = prov.get("attestation_bundles", [])
            if not bundles:
                continue

            for bundle_data in bundles:
                attestations = bundle_data.get("attestations", [])
                if not attestations:
                    continue
                att = attestations[0]

                # Extract individual PEP 740 attestation for pypi-attestations CLI
                att_file = proofs_dir / f"{f.name}.publish.attestation"
                att_file.write_text(json.dumps(att))
                print(f"  {index_name}: {f.name} — .publish.attestation extracted")

                # Restructure into cosign-compatible bundle
                vm = att.get("verification_material", {})
                cosign_bundle = {
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
                cosign_file = proofs_dir / f"{f.name}.cosign-bundle.json"
                cosign_file.write_text(json.dumps(cosign_bundle, indent=2))
                print(f"  {index_name}: {f.name} — cosign bundle extracted")


# -- Main ------------------------------------------------------------------


def main() -> int:
    version = get_version()
    tag = f"{TAG_PREFIX}{version}"

    DIST_DIR.mkdir(exist_ok=True)
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. GitHub Release
    print(f"Downloading {tag} from {REPO_SLUG}...")
    if not download_github_release(version):
        return 1

    # 2. GitHub Attestations
    print("\nFetching GitHub attestations...")
    fetch_gh_attestations(version)

    # 3. PyPI / TestPyPI provenance + extraction
    print("\nFetching PyPI/TestPyPI provenance...")
    extract_pypi_proofs(version)

    # Summary
    dist_files = [f for f in sorted(DIST_DIR.iterdir()) if f.is_file()]
    gh_files = [f for f in sorted(PROOFS_DIR.iterdir()) if f.is_file() and f.name != ".gitignore"]

    print(f"\ndist/ ({len(dist_files)} files):")
    for f in dist_files:
        print(f"  {f.name}")

    print(f"\nproofs/github/ ({len(gh_files)} files):")
    for f in gh_files:
        print(f"  {f.name}")

    for index_name, _base_url in PYPI_INDEXES:
        proofs_dir = REPO_ROOT / "proofs" / index_name
        if proofs_dir.is_dir():
            files = [
                f for f in sorted(proofs_dir.iterdir()) if f.is_file() and f.name != ".gitignore"
            ]
            print(f"\nproofs/{index_name}/ ({len(files)} files):")
            for f in files:
                print(f"  {f.name}")

    print(f"\nVerify with: uv run python scripts/verify_provenance.py {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
