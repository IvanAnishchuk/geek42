"""Verify that all commits being pushed are signed.

Uses PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF environment variables
(set by the pre-commit framework for pre-push hooks) to determine the
exact commit range. This is a quick local check — GitHub branch
protection does the authoritative enforcement.

Usage:
    uv run python scripts/check_signatures.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def main() -> int:
    git = shutil.which("git") or "git"

    from_ref = os.environ.get("PRE_COMMIT_FROM_REF", "")
    to_ref = os.environ.get("PRE_COMMIT_TO_REF", "")

    if not from_ref or not to_ref:
        # Not running via pre-commit pre-push hook — skip
        print("No PRE_COMMIT_FROM_REF/TO_REF set, skipping signature check.")
        return 0

    result = subprocess.run(  # noqa: S603 — args are list literals, no shell
        [git, "log", "--format=%H %G? %s", f"{from_ref}..{to_ref}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: git log failed for {from_ref}..{to_ref}", file=sys.stderr)
        return 1

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return 0  # nothing to push

    failures = 0
    for line in lines:
        parts = line.split(" ", 2)
        if len(parts) < 3:
            print(f"WARNING: could not parse git log line: {line!r}", file=sys.stderr)
            continue
        commit_hash, sig_status, subject = parts
        short = commit_hash[:7]
        # G = good signature
        # U = good signature, untrusted key
        # X = good signature, expired
        # E = cannot be checked (e.g. missing key) — accepted for local check,
        #     GitHub branch protection does authoritative enforcement
        # N = no signature
        # B = bad signature
        if sig_status in ("G", "U", "X", "E"):
            continue
        if sig_status == "N":
            print(f"FAIL: unsigned commit {short}: {subject}")
        elif sig_status == "B":
            print(f"FAIL: bad signature on {short}: {subject}")
        else:
            print(f"FAIL: signature status '{sig_status}' on {short}: {subject}")
        failures += 1

    if failures:
        print(f"\n{failures} unsigned/invalid commit(s) found.", file=sys.stderr)
        print("All commits must be signed. See CONTRIBUTING.md for setup.", file=sys.stderr)
        return 1

    print(f"All {len(lines)} commit(s) are signed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
