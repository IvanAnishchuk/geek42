"""Download a geek42 release from GitHub to dist/.

Downloads wheel, sdist, and proof files (sigstore bundles, SBOM,
checksums, SLSA provenance) from a GitHub Release. Distribution
files go to dist/, proof files to proofs/github/.

Usage:
    uv run python scripts/download_release.py [VERSION]
    uv run python scripts/download_release.py 0.4.2a7
    uv run python scripts/download_release.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_SLUG = "IvanAnishchuk/geek42"
DIST_DIR = REPO_ROOT / "dist"
PROOFS_DIR = REPO_ROOT / "proofs" / "github"

DIST_EXTENSIONS = (".whl", ".tar.gz")


def get_version() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].removeprefix("v")
    init = REPO_ROOT / "src" / "geek42" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    print("Could not detect version. Pass it as an argument.")
    sys.exit(1)


def main() -> int:
    version = get_version()
    tag = f"v{version}"

    DIST_DIR.mkdir(exist_ok=True)
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {tag} from {REPO_SLUG}...")

    # Download everything to a single temp location, then sort
    gh = shutil.which("gh") or "gh"
    result = subprocess.run(  # noqa: S603 — args are list literals, no shell
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
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error: GitHub Release {tag} not found")
        if result.stderr:
            print(f"  {result.stderr.strip()}")
        return 1

    # Move non-distribution files to proofs/github/
    moved = 0
    for f in sorted(DIST_DIR.iterdir()):
        if not any(f.name.endswith(ext) for ext in DIST_EXTENSIONS):
            target = PROOFS_DIR / f.name
            if not target.exists():
                f.rename(target)
                moved += 1
            else:
                f.unlink()  # duplicate, already in proofs

    dist_files = [f for f in sorted(DIST_DIR.iterdir()) if f.is_file()]
    proof_files = [
        f for f in sorted(PROOFS_DIR.iterdir()) if f.is_file() and f.name != ".gitignore"
    ]

    print(f"\ndist/ ({len(dist_files)} files):")
    for f in dist_files:
        print(f"  {f.name}")

    print(f"\nproofs/github/ ({len(proof_files)} files):")
    for f in proof_files:
        print(f"  {f.name}")

    print(f"\nVerify with: uv run python scripts/verify_provenance.py {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
