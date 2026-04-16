"""Verify that all commits on the current branch are signed.

Checks commits between the remote tracking branch and HEAD. Unsigned
or badly signed commits are reported as errors.

Usage:
    uv run python scripts/check_signatures.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> int:
    git = shutil.which("git") or "git"

    # Find the remote tracking branch to compare against
    result = subprocess.run(  # noqa: S603 — args are list literals
        [git, "log", "--format=%H %G? %s", "@{upstream}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # No upstream — check all commits on branch vs main
        result = subprocess.run(  # noqa: S603
            [git, "log", "--format=%H %G? %s", "origin/main..HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        print("WARNING: could not determine commit range for signature check")
        return 0

    lines = [line for line in result.stdout.strip().splitlines() if line]
    if not lines:
        return 0  # nothing to push

    failures = 0
    for line in lines:
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        commit_hash, sig_status, subject = parts
        short = commit_hash[:7]
        # G=good, U=good untrusted, E=expired (GitHub merge commits)
        # N=no signature, B=bad signature, X=expired signature
        if sig_status in ("G", "U", "E"):
            continue
        if sig_status == "N":
            print(f"FAIL: unsigned commit {short}: {subject}")
        elif sig_status == "B":
            print(f"FAIL: bad signature on {short}: {subject}")
        else:
            print(f"FAIL: signature status '{sig_status}' on {short}: {subject}")
        failures += 1

    if failures:
        print(f"\n{failures} unsigned/invalid commit(s) found.")
        print("All commits must be signed. See CONTRIBUTING.md for setup.")
        return 1

    print(f"All {len(lines)} commit(s) are signed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
