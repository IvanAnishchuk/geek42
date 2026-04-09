<!--
Thanks for contributing to geek42!

Please follow these conventions:
- Use Conventional Commits for the PR title (feat/fix/docs/...)
- Sign your commits (GPG, SSH, or sigstore gitsign)
- Sign off your commits with `git commit -s` (DCO)

See CONTRIBUTING.md for details.
-->

## Summary

<!-- What does this PR do and why? Link to issue if applicable. -->

## Changes

<!-- Bullet list of concrete changes -->

-
-

## Checklist

- [ ] Tests added/updated for new behavior
- [ ] `uv run pytest` passes locally
- [ ] `uv run pre-commit run --all-files` passes locally
- [ ] `uv run python scripts/audit.py` passes (if touching deps)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] Docs updated if the public interface changed
- [ ] Commits are signed (`-S`) and DCO-signed off (`-s`)
- [ ] Commit messages follow [Conventional Commits](https://conventionalcommits.org)

## Security impact

<!--
If this change affects the supply-chain security posture
(permissions, workflows, dependencies, crypto, etc.), describe the
impact here. Otherwise write "none".
-->

none
