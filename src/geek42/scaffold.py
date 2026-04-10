"""Scaffold a complete GLEP 42 news repository.

Creates the standard directory layout, pre-commit hooks, CI workflow,
and tool configuration so that a news repo works identically in local
development and CI from the first commit.
"""

from __future__ import annotations

from pathlib import Path

from .parser import NEWS_SUBDIR

# -- public API --------------------------------------------------------------


def scaffold(root: Path, *, title: str, author: str, name: str = "") -> list[Path]:
    """Create a full news repository scaffold at *root*.

    Existing files are never overwritten. Returns the paths that were
    created.
    """
    if not name:
        name = root.name

    files = _render_templates(title=title, author=author, name=name)
    created: list[Path] = []

    for relpath, content in files.items():
        target = root / relpath
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(target)

    # Ensure the news directory exists (even if empty)
    (root / NEWS_SUBDIR).mkdir(parents=True, exist_ok=True)

    return created


# -- template rendering -------------------------------------------------------


def _render_templates(*, title: str, author: str, name: str) -> dict[str, str]:
    return {
        "geek42.toml": _GEEK42_TOML.format(title=title, author=author),
        ".pre-commit-config.yaml": _PRE_COMMIT_YAML,
        ".github/workflows/ci.yml": _CI_YML.format(name=name),
        "pyproject.toml": _PYPROJECT_TOML.format(name=name),
        "README.md": _README_MD.format(title=title),
        ".gitignore": _GITIGNORE,
        "metadata/layout.conf": _LAYOUT_CONF.format(name=name),
    }


# -- template strings ---------------------------------------------------------

_GEEK42_TOML = """\
title = "{title}"
author = "{author}"
description = "News Items"
base_url = ""
output_dir = "_site"
data_dir = ".geek42"
language = "en"

# OpenPGP key ID for Manifest signing (used by `geek42 sign`):
# signing_key = "0xABCD1234"

[[sources]]
name = "local"
url = "."

# To read news from remote repositories, add more sources:
# [[sources]]
# name = "gentoo"
# url = "https://anongit.gentoo.org/git/data/glep42-news-gentoo.git"
# branch = "master"
"""

_PRE_COMMIT_YAML = """\
repos:
  # -- whitespace & formatting ------------------------------------------------
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: mixed-line-ending
        args: [--fix=lf]
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: fix-byte-order-marker
      - id: check-case-conflict

  # -- geek42 news checks ----------------------------------------------------
  - repo: local
    hooks:
      - id: lint-news
        name: geek42 lint
        entry: uv tool run geek42 lint metadata/news
        language: system
        always_run: true
        pass_filenames: false

      - id: compile-blog
        name: geek42 compile-blog
        entry: uv tool run geek42 compile-blog
        language: system
        always_run: true
        pass_filenames: false

      - id: verify-manifest
        name: verify Manifest
        entry: uv tool run geek42 verify
        language: system
        always_run: true
        pass_filenames: false
        stages: [pre-push]
"""

_CI_YML = """\
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions: {{}}

jobs:
  check:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6

      # -- whitespace & formatting --
      - name: Check trailing whitespace
        run: |
          ! grep -rn '[[:blank:]]$' metadata/news/ && echo "OK: no trailing whitespace"
      - name: Check line endings (LF only)
        run: |
          ! grep -rPl '\\r' metadata/news/ && echo "OK: no CRLF"
      - name: Check final newline
        run: |
          bad=0
          for f in $(find metadata/news -name '*.txt'); do
            [ -s "$f" ] && [ "$(tail -c1 "$f" | xxd -p)" != "0a" ] && \
              echo "missing newline: $f" && bad=1
          done
          [ "$bad" -eq 0 ] && echo "OK: all files end with newline"
          exit $bad

      # -- GLEP 42 lint --
      - name: Lint news items
        run: uv tool run geek42 lint metadata/news

      # -- Manifest checksums & signature --
      - name: Verify Manifest (geek42)
        run: uv tool run geek42 verify
      - name: Verify Manifest (gemato)
        run: uv tool run gemato verify .

      # -- compiled output is up to date --
      - name: Compile blog
        run: uv tool run geek42 compile-blog
      - name: Confirm no uncommitted changes
        run: |
          git diff --exit-code -- news/ README.md || \
            (echo "::error::Compiled output is stale" && exit 1)

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: check
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Build site
        run: uv tool run geek42 build --no-pull
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - id: deployment
        uses: actions/deploy-pages@v4
"""

_PYPROJECT_TOML = """\
[project]
name = "{name}"
version = "0.0.0"
description = "GLEP 42 news repository"
requires-python = ">=3.13"

[dependency-groups]
dev = [
    "geek42",
    "gemato",
    "pre-commit>=4.0",
]
"""

_README_MD = """\
# {title}

<!-- geek42:news-index:start -->
## News

| Date | Title | Author |
|------|-------|--------|

<!-- geek42:news-index:end -->

## Contributing

```sh
# Write a news item
geek42 new

# Commit (compiles blog automatically via pre-commit)
geek42 commit

# Push
geek42 push
```

## Setup

```sh
uv sync --dev
pre-commit install
```
"""

_GITIGNORE = """\
_site/
.geek42/
.reports/
*.pyc
"""

_LAYOUT_CONF = """\
# Repository layout metadata
repo-name = {name}
"""
