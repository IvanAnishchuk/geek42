# geek42 Style Guide for Gemini Code Assist

## Language and tooling

- Python 3.13+, src layout, hatchling build backend
- ruff for linting (line-length 100) and formatting
- ty for type checking
- pytest with 75% coverage floor
- uv as package manager (never raw pip)
- No shell scripts or Makefiles — Python scripts only

## Code conventions

- Conventional Commits required for all commit messages
- Narrow exception types — no bare `except Exception`
- All `# noqa` comments must document why
- subprocess calls must use list args, never `shell=True`
- URLs must be validated before fetching
- Prefer editing existing files over creating new ones

## Security

- Supply-chain: SLSA L3, sigstore, PEP 740 attestations on every release
- All actions in workflows pinned by SHA with version comment
- Trust anchors derived from pyproject.toml, not hardcoded

## Changelog

- Every PR must update CHANGELOG.md under [Unreleased]
- Versions follow PEP 440 (not SemVer)
