# User Guide

A walkthrough of the complete geek42 workflow — from creating a news
repository to publishing it as a static site.

---

## 1. Create a new news repository

```console
$ mkdir my-news && cd my-news
$ git init
Initialized empty Git repository in /home/user/my-news/.git/

$ geek42 init --title "Gentoo Hardened News"
  + geek42.toml
  + .pre-commit-config.yaml
  + .github/workflows/lint.yml
  + .github/workflows/manifest.yml
  + .github/workflows/deploy.yml
  + .github/dependabot.yml
  + .yamllint.yml
  + pyproject.toml
  + README.md
  + .gitignore
  + metadata/layout.conf

11 file(s) created.
```

This creates the full directory structure:

```
my-news/
  metadata/
    news/           # news items go here
    layout.conf     # repo metadata
  .pre-commit-config.yaml
  .github/workflows/
  geek42.toml
  README.md
  ...
```

## 2. Set up pre-commit hooks

```console
$ uv sync --dev
$ pre-commit install
pre-commit installed at .git/hooks/pre-commit

$ pre-commit install --hook-type commit-msg
pre-commit installed at .git/hooks/commit-msg

$ pre-commit install --hook-type pre-push
pre-commit installed at .git/hooks/pre-push
```

## 3. Write your first news item

```console
$ geek42 new
```

This opens your `$EDITOR` with a template:

```
Title:
Author: Your Name <your@email.org>
Posted: 2026-04-10
Revision: 1
News-Item-Format: 2.0

Write your news item body here.

Wrap lines at 72 characters. Separate paragraphs with
blank lines.
```

Fill in the title and body, save, and quit. geek42 lints the file
and places it in `metadata/news/`:

```console
Created metadata/news/2026-04-10-my-first-post/2026-04-10-my-first-post.en.txt
```

## 4. Commit

```console
$ geek42 commit
Manifest updated.
Committed: feat(news): add 2026-04-10-my-first-post
```

This runs `compile-blog` (generates `news/*.md` and updates the
README index), regenerates the Manifest, stages everything, and
commits with an auto-generated Conventional Commits message.

To provide your own message:

```console
$ geek42 commit -m "feat(news): announce the FlexiBLAS migration"
```

## 5. Push

```console
$ geek42 push
Everything up-to-date
```

The CI pipeline runs automatically:
- Pre-commit hooks (whitespace, YAML, Markdown formatting)
- News item linting (`geek42 lint`)
- Manifest verification (`gemato verify`)
- Blog output staleness check
- GitHub Pages deployment (on main)

## 6. Read news in the terminal

```console
$ geek42 list
                         News Items (1 unread)
┏━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     ┃ Date       ┃ Title            ┃ Source ┃ ID                      ┃
┡━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ *   │ 2026-04-10 │ My First Post    │ local  │ 2026-04-10-my-first-p…  │
└─────┴────────────┴──────────────────┴────────┴─────────────────────────┘

$ geek42 read my-first
┌─────────── My First Post ───────────┐
│ Your Name <your@email.org>          │
│ 2026-04-10  rev 1  [local]          │
└─────────────────────────────────────┘

This is the body of my first news post...

$ geek42 read-new
1 unread item(s)
...
```

## 7. Revise an existing item

```console
$ geek42 revise my-first
Revising 2026-04-10-my-first-post
```

This opens the item in `$EDITOR` with the revision bumped and the
posted date updated to today. Save and quit to apply.

## 8. Build a static site

```console
$ geek42 build --no-pull
Collecting news items...
Building site...
Done. 1 posts -> _site/

$ ls _site/
atom.xml  index.html  markdown/  posts/  rss.xml  style.css
```

## 9. Lint news files

```console
$ geek42 lint metadata/news
0 error(s), 0 warning(s)

$ geek42 lint --strict metadata/news
0 error(s), 0 warning(s)
```

## 10. Sign and verify Manifests

```console
# Generate/update Manifest tree (unsigned)
$ geek42 sign
Manifest updated.

# Sign with a GPG key (from config or --key)
$ geek42 sign --key ivan@agorism.org
Manifest updated and signed with key ivan@agorism.org

# Verify
$ geek42 verify
Verified.
```

## 11. Work on a remote news repo

You can use `-C` to operate on any directory:

```console
$ geek42 list -C ~/src/gentoo/newsrepo
$ geek42 new -C ~/src/gentoo/newsrepo
$ geek42 commit -C ~/src/gentoo/newsrepo
```

## 12. Check deployment status

```console
$ geek42 deploy-status
IvanAnishchuk/geek42

  Pages: https://ivananishchuk.github.io/geek42/
  Status: built
  Build:  built 2026-04-10 18:30 (abc1234)
  CI:    ✓ success fix: coverage paths (4e4d7ad)
```

---

## Quick reference

| Task | Command |
|------|---------|
| Create repo | `geek42 init --title "My News"` |
| Write item | `geek42 new` |
| Revise item | `geek42 revise <id>` |
| List items | `geek42 list` |
| Read item | `geek42 read <id>` |
| Read all new | `geek42 read-new` |
| Lint | `geek42 lint metadata/news` |
| Build site | `geek42 build --no-pull` |
| Compile blog | `geek42 compile-blog` |
| Commit | `geek42 commit` |
| Push | `geek42 push` |
| Sign Manifest | `geek42 sign` |
| Verify Manifest | `geek42 verify` |
| Deploy status | `geek42 deploy-status` |
