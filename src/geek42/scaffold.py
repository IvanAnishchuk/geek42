"""Scaffold a complete GLEP 42 news repository.

Creates the standard directory layout, pre-commit hooks, CI workflows,
and tool configuration matching the Gentoo overlay conventions so that
a news repo works identically in local development and CI.
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
        ".github/workflows/lint.yml": _LINT_YML,
        ".github/workflows/manifest.yml": _MANIFEST_YML,
        ".github/workflows/deploy.yml": _DEPLOY_YML,
        ".github/dependabot.yml": _DEPENDABOT_YML,
        ".yamllint.yml": _YAMLLINT_YML,
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

# ---- pre-commit (mirrors localrepo pattern) ----

_PRE_COMMIT_YAML = """\
# Pre-commit hooks for GLEP 42 news repository
# Install: uv sync --dev && pre-commit install

repos:
  # -- text hygiene -----------------------------------------------------------
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
        exclude: '(/|^)Manifest$'
      - id: mixed-line-ending
        args: [--fix=lf]
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=1024']

  # -- YAML lint --------------------------------------------------------------
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.38.0
    hooks:
      - id: yamllint
        args: ['--strict', '-c', '.yamllint.yml']

  # -- Markdown formatting ----------------------------------------------------
  - repo: https://github.com/executablebooks/mdformat
    rev: 0.7.22
    hooks:
      - id: mdformat
        args: ['--wrap=keep', '--number']
        additional_dependencies:
          - mdformat-gfm
          - mdformat-tables
          - mdformat-frontmatter

  # -- geek42 / gemato local hooks -------------------------------------------
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

      - id: gemato-sign
        name: update and sign Manifest tree
        description: >-
          Run gemato update to refresh the Manifest tree.
          Fails if Manifest files changed so you can stage them.
        entry: >-
          bash -c '
          command -v gemato >/dev/null ||
            { echo "gemato not installed (uv tool install gemato);"
              echo "to skip: SKIP=gemato-sign git commit"; exit 1; };
          uv tool run geek42 sign &&
          git diff --exit-code --name-only -- Manifest
            ":(glob)**/Manifest" ||
            { echo "Manifest tree updated — stage and re-commit";
              exit 1; }'
        language: system
        pass_filenames: false

      - id: verify-manifest
        name: verify Manifest tree
        entry: uv tool run geek42 verify
        language: system
        always_run: true
        pass_filenames: false
        stages: [pre-push]
"""

# ---- CI: lint (portable pre-commit hooks) ----

_LINT_YML = """\
name: lint

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: pre-commit/action@v3.0.1
        env:
          SKIP: gemato-sign,verify-manifest
"""

# ---- CI: manifest verification ----

_MANIFEST_YML = """\
name: manifest

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: astral-sh/setup-uv@v6

      - name: Regenerate Manifests
        run: uv tool run geek42 sign
      - name: Verify Manifests are up to date
        run: |
          git diff --exit-code --name-only -- Manifest \
            ':(glob)**/Manifest' ':(glob)**/Manifest.gz' || \\
            { echo "::error::Manifests are stale"; exit 1; }
          echo "All Manifests up to date"

      - name: Verify Manifest tree (gemato)
        run: uv tool run gemato verify --keep-going .

      - name: Verify compiled blog is up to date
        run: |
          uv tool run geek42 compile-blog
          git diff --exit-code -- news/ README.md || \\
            { echo "::error::Compiled output is stale"; exit 1; }
"""

# ---- CI: GitHub Pages deploy ----

_DEPLOY_YML = """\
name: deploy

on:
  push:
    branches: [main]

permissions: {{}}

jobs:
  deploy:
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

# ---- dependabot ----

_DEPENDABOT_YML = """\
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "ci"
      include: "scope"
"""

# ---- yamllint ----

_YAMLLINT_YML = """\
extends: relaxed

rules:
  line-length: disable
  document-start: disable
  truthy:
    check-keys: false
"""

# ---- pyproject.toml ----

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

# ---- README ----

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

# Commit (compiles blog and updates Manifests via pre-commit)
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

# ---- gitignore ----

_GITIGNORE = """\
_site/
.geek42/
.reports/
*.pyc
"""

# ---- metadata/layout.conf ----

_LAYOUT_CONF = """\
repo-name = {name}
"""
