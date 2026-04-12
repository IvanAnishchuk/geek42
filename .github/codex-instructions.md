# Codex instructions for geek42

## Project

Pure Python CLI tool (Python 3.13+) using uv, hatchling, typer, rich,
pydantic. Converts GLEP 42 Gentoo news repos into static blogs.

## Conventions

- **Commits:** Conventional Commits format required (`feat:`, `fix:`, etc.)
- **Formatting:** ruff (line length 100, target py313)
- **Type checking:** ty
- **Testing:** pytest with 75% coverage floor
- **Package manager:** uv (never raw pip)
- Prefer Python scripts over shell scripts or Makefiles for tooling

## Security

- All subprocess calls use list args (no shell=True)
- Exception catches should be as narrow as possible
- URLs must be validated before fetching
- Every noqa comment must document why it's necessary
- Supply-chain: SLSA L3, sigstore, PEP 740 attestations on every release
- All actions in workflows pinned by SHA with version comment

## Changelog

- Every PR must have a corresponding `CHANGELOG.md` entry under `[Unreleased]`
- When reviewing, check that user-visible changes have changelog entries
- Changelog uses PEP 440 versions, not SemVer

## Review process

When reviewing PRs:
- Triage every comment, including low-confidence hidden ones
- For actionable findings: fix in the PR or create a GitHub issue and link it
- Never dismiss comments without explicit owner confirmation
- Reply with linked issue number or reason before resolving conversations
- After changes are made, re-review before approving
- Verify that CHANGELOG.md is updated for user-visible changes

This applies to all reviewers: Copilot, Gemini Code Assist, CodeRabbit, Codex, and humans.
