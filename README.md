# geek42

<!-- Build & test -->
[![CI](https://github.com/congentoo/geek42/actions/workflows/ci.yml/badge.svg)](https://github.com/congentoo/geek42/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/congentoo/geek42/python-coverage-comment-action-data/badge.svg)](https://github.com/congentoo/geek42/tree/python-coverage-comment-action-data)
[![Tests](https://img.shields.io/github/actions/workflow/status/congentoo/geek42/ci.yml?label=tests&branch=main)](https://github.com/congentoo/geek42/actions/workflows/ci.yml)

<!-- Security -->
[![CodeQL](https://github.com/congentoo/geek42/actions/workflows/codeql.yml/badge.svg)](https://github.com/congentoo/geek42/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/congentoo/geek42/badge)](https://scorecard.dev/viewer/?uri=github.com/congentoo/geek42)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/XXXXX/badge)](https://www.bestpractices.dev/projects/XXXXX)
[![SLSA Level 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![StepSecurity](https://img.shields.io/badge/runners-hardened-blue)](https://app.stepsecurity.io/github/congentoo/geek42)

<!-- Packaging -->
[![PyPI](https://img.shields.io/pypi/v/geek42)](https://pypi.org/project/geek42/)
[![Python](https://img.shields.io/pypi/pyversions/geek42)](https://pypi.org/project/geek42/)
[![Downloads](https://img.shields.io/pypi/dm/geek42)](https://pypi.org/project/geek42/)

<!-- Project health -->
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: CC0-1.0](https://img.shields.io/badge/license-CC0--1.0-lightgrey)](LICENSE.md)

Convert [GLEP 42](https://www.gentoo.org/glep/glep-0042.html) Gentoo news repositories into a static blog with RSS/Atom feeds, Markdown exports, and a terminal reader — no `eselect news` required.

## Features

- **Local-first blog** — write news items in your git repo, push to publish
- **Static site** — generates a self-contained HTML site ready for GitHub Pages or any static host
- **Pre-commit blog compiler** — auto-generates Markdown files and a README index on commit
- **RSS + Atom feeds** — standards-compliant feeds generated from stdlib (no extra deps)
- **Markdown exports** — each news item exported as `.md` with YAML frontmatter (Jekyll/Hugo compatible)
- **Compose and revise** — `new` and `revise` commands open `$EDITOR` with templates and auto-lint
- **Full GLEP 42 metadata** — packages, architectures, profiles, revision, format version all preserved
- **Multiple sources** — optionally aggregate news from remote GLEP 42 git repos
- **Terminal reader** — `list` and `read` commands with Rich formatting
- **Semantic HTML** — Schema.org JSON-LD, Open Graph, proper `<article>`/`<time>`/`<address>` elements
- **Dark mode** — respects `prefers-color-scheme`

## Install

Requires Python 3.13+.

```sh
uv tool install geek42
```

## Quickstart

```sh
# Create a git repo for your news blog
mkdir my-blog && cd my-blog
git init

# Initialize configuration
geek42 init

# Write your first post (opens $EDITOR)
geek42 new

# Commit (pre-commit hook compiles Markdown + README index)
git add -A && git commit -m "feat: first post"

# Push (GitHub Actions builds static site)
git push
```

## Configuration

`geek42.toml` (created by `geek42 init`):

```toml
title = "My News"
author = "Your Name <you@example.org>"
description = "News Items"
base_url = ""
output_dir = "_site"
data_dir = ".geek42"
language = "en"

[[sources]]
name = "local"
url = "."

# To read news from remote repositories:
# [[sources]]
# name = "gentoo"
# url = "https://anongit.gentoo.org/git/data/glep42-news-gentoo.git"
# branch = "master"
```

## CLI Commands

```
geek42 init              Create a default geek42.toml
geek42 new               Create a new news item (opens $EDITOR)
geek42 new -e nano       Use a specific editor
geek42 new -C <dir>      Create a news item in a specific directory
geek42 revise <id>       Revise an existing item (bump rev, open $EDITOR)
geek42 lint <path>       Lint a news file or repository directory
geek42 lint --strict .   Treat warnings as errors
geek42 compile-blog      Compile Markdown files and update README index
geek42 build --no-pull   Build static site from local items
geek42 list              List news items in a Rich table
geek42 list -C <dir>     List news items from a specific directory
geek42 read <id>         Read a specific news item in the terminal
geek42 pull              Clone or update remote news sources
geek42 build             Pull remote sources and build the static site
```

Most commands accept `--directory` / `-C` to operate on a directory
other than the current one. Config, data, and output paths are resolved
relative to that directory.

### Lint codes

| Code | Severity | Description |
|------|----------|-------------|
| E001 | error | Missing required header |
| E002 | error | Invalid date format |
| E003 | error | Invalid revision number |
| E004 | error | Unknown News-Item-Format |
| E005 | error | Format 1.0 missing Content-Type |
| E006 | error | Empty body |
| E007 | error | No blank line between headers and body |
| E008 | error | Missing news file in directory |
| E010 | error | Malformed header line |
| W001 | warning | Title exceeds 50 characters |
| W002 | warning | Body line exceeds 72 characters |
| W003 | warning | Trailing whitespace |
| W004 | warning | Author not in `Name <email>` format |
| W005 | warning | File name doesn't match directory name |
| W006 | warning | Directory name doesn't match GLEP 42 pattern |

## Repository Layout

News items live under `metadata/news/` (standard portage layout):

```
my-blog/
  metadata/news/
    2025-11-30-flexiblas-migration/
      2025-11-30-flexiblas-migration.en.txt
    ...
  geek42.toml
```

Dedicated news-only repos (like `glep42-news-gentoo.git`) that store
items at the root are also supported — geek42 auto-detects the layout.

## Output Structure

```
_site/
  index.html            Main listing page
  style.css             Stylesheet (dark mode aware)
  rss.xml               RSS 2.0 feed
  atom.xml              Atom 1.0 feed
  posts/
    2025-11-30-flexiblas-migration.html
    ...
  markdown/
    2025-11-30-flexiblas-migration.md
    ...
```

## Development

```sh
uv sync

# Run tests with coverage
uv run pytest

# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run ty check
```

## GitHub Pages Deployment

Add a workflow like `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv tool install geek42
      - run: geek42 build --no-pull
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Documentation

- [docs/news-format.md](docs/news-format.md) — GLEP 42 format spec, blog
  maintenance workflow, reading other people's news
- [docs/security-setup.md](docs/security-setup.md) — repo owner security
  configuration checklist

## Security

- **Disclosure policy**: [SECURITY.md](SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md) (signed commits required)
- **Supply chain**: Releases are built by GitHub Actions with SLSA Level 3
  provenance, signed with sigstore, and published to PyPI via OIDC trusted
  publishing. Every release ships with a CycloneDX SBOM and build attestations.

### Verifying a release

```sh
# Download wheel and attestations
gh release download v0.1.0 --repo congentoo/geek42

# Verify sigstore signature (requires `uv tool install sigstore`)
uv tool run sigstore verify identity \
    --cert-identity-regexp '^https://github\.com/congentoo/geek42/\.github/workflows/release\.yml@' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    --bundle geek42-0.1.0-py3-none-any.whl.sigstore \
    geek42-0.1.0-py3-none-any.whl

# Verify GitHub build provenance
gh attestation verify geek42-0.1.0-py3-none-any.whl --owner congentoo

# Verify SLSA L3 provenance
slsa-verifier verify-artifact \
    --provenance-path geek42-provenance.intoto.jsonl \
    --source-uri github.com/congentoo/geek42 \
    --source-tag v0.1.0 \
    geek42-0.1.0-py3-none-any.whl
```

## License

[CC0 1.0 Universal](LICENSE.md) — public domain dedication.
