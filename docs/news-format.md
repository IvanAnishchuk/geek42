# GLEP 42 News Repository Format and Workflow

This document explains the GLEP 42 news item format, how to maintain
your own news repository as a personal blog, and how to subscribe to
and read news from other people's repositories.

## The GLEP 42 News Format

[GLEP 42](https://www.gentoo.org/glep/glep-0042.html) defines a simple
plain-text format for distributing news items through git repositories.
Each news item is a directory containing one or more text files with
RFC 822-style headers and a plain-text body.

### Repository Layout

A news repository is a git repo with this structure:

```
my-news/
  2025-01-15-welcome/
    2025-01-15-welcome.en.txt
  2025-03-20-new-project/
    2025-03-20-new-project.en.txt
    2025-03-20-new-project.de.txt    (optional translation)
  2025-04-01-migration-guide/
    2025-04-01-migration-guide.en.txt
  README
```

Each directory name is the **item identifier**: a date followed by a
short name. The short name uses only `a-z`, `0-9`, `+`, `-`, `_` and
is recommended to be at most 20 characters.

Inside each directory is at least one file named
`{identifier}.{language}.txt`. The `.en.txt` file is authoritative;
other languages are translations.

### News Item File Format

Each file has two sections separated by a blank line: **headers** and
**body**.

```
Title: Migration to New Build System
Author: Jane Doe <jane@example.org>
Author: John Smith <john@example.org>
Posted: 2025-04-01
Revision: 1
News-Item-Format: 2.0
Display-If-Installed: dev-build/meson
Display-If-Keyword: amd64
Display-If-Profile: default/linux/amd64/23.0

Starting next month, we are migrating from autotools to meson
for all packages in the dev-build category.

Users who have dev-build/meson installed should read the
migration guide at https://example.org/meson-migration

Steps to prepare:
1. Update your world set
2. Review /etc/portage/package.use for affected packages
3. Run emerge --sync after the migration date
```

### Header Reference

#### Required Headers

| Header | Format | Description |
|--------|--------|-------------|
| `Title` | Plain text, max 50 chars | Short headline for the item |
| `Author` | `Name <email>` | One per line, repeatable for multiple authors |
| `Posted` | `YYYY-MM-DD` | Publication date (UTC) |
| `Revision` | Positive integer | Starts at `1`, incremented on each edit |
| `News-Item-Format` | `1.0` or `2.0` | Format version (use `2.0` for new items) |

#### Optional Headers

| Header | Format | Description |
|--------|--------|-------------|
| `Content-Type` | `text/plain` | Required only for format 1.0 |
| `Translator` | `Name <email>` | For translated files, repeatable |
| `Display-If-Installed` | Package atom | Show if package is installed (repeatable) |
| `Display-If-Keyword` | Architecture | Show if arch matches (repeatable) |
| `Display-If-Profile` | Profile path | Show if profile matches (repeatable, supports `*` wildcard in 2.0) |

#### Display-If Logic

The filtering rules are:

- **OR** within each header type: if *any* `Display-If-Installed`
  matches, that type is satisfied
- **AND** across types: all types that appear must be satisfied
- If **no** `Display-If-*` headers are present, the item is shown to
  everyone

For a personal blog, you typically omit all `Display-If-*` headers so
every item is visible to all readers.

### Body Format

- Plain UTF-8 text
- Wrap lines at 72 characters
- Separate paragraphs with blank lines
- URLs may be included inline
- No markup or tab characters

### Format 1.0 vs 2.0

| Feature | 1.0 | 2.0 |
|---------|-----|-----|
| `Content-Type` header | Required | Absent |
| `Display-If-Installed` syntax | EAPI 0 atoms | EAPI 5 atoms (slots, USE) |
| `Display-If-Profile` wildcards | No | `*` wildcard supported |

Use format 2.0 for all new items.

## Maintaining Your Blog

### Initial Setup

```sh
# Install geek42
uv tool install geek42

# Create a git repo for your news
mkdir my-blog && cd my-blog
git init

# Initialize geek42 configuration
geek42 init
```

Edit `geek42.toml` to point the first source at your own repo:

```toml
title = "My Tech Blog"
description = "Notes on Gentoo, systems, and code"
base_url = "https://IvanAnishchuk.github.io/newsrepo"
author = "Your Name <you@example.org>"
output_dir = "_site"
data_dir = ".geek42"
language = "en"

[[sources]]
name = "mine"
url = "."
branch = "main"
```

### Writing a New Post

```sh
geek42 new
```

This opens your `$VISUAL`/`$EDITOR` with a template pre-filled with
today's date and your git author info:

```
Title:
Author: Your Name <you@example.org>
Posted: 2025-04-09
Revision: 1
News-Item-Format: 2.0

Write your news item body here.

Wrap lines at 72 characters. Separate paragraphs with
blank lines.
```

Fill in the title and replace the placeholder body with your content.
When you save and exit, geek42 runs the linter. If there are errors, it
offers to re-open the editor. Once valid, the file is placed in the
correct directory:

```
2025-04-09-your-title/
  2025-04-09-your-title.en.txt
```

You can also specify the editor and target source explicitly:

```sh
geek42 new --editor "code --wait" --source mine
```

### Revising a Post

To update an existing post (fix a typo, add info):

```sh
geek42 revise 2025-04-09-your-title
```

This opens a copy with the revision number bumped and the date updated
to today. After editing, the file is written back to the original
location.

You can use a substring match:

```sh
geek42 revise your-title
```

### Linting

Check your posts for format compliance:

```sh
# Lint a single file
geek42 lint 2025-04-09-your-title/2025-04-09-your-title.en.txt

# Lint the entire repo
geek42 lint .

# Treat warnings as errors (useful in CI)
geek42 lint --strict .
```

### Building the Site

```sh
geek42 build
```

This generates a static site in `_site/` with:

- `index.html` -- listing of all posts, newest first
- `posts/{id}.html` -- individual post pages
- `markdown/{id}.md` -- Markdown export with YAML frontmatter
- `rss.xml` -- RSS 2.0 feed
- `atom.xml` -- Atom 1.0 feed
- `style.css` -- stylesheet with dark mode support

### Publishing to GitHub Pages

Commit your news items and push. Use a GitHub Actions workflow
to build and deploy:

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
      - run: geek42 build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - id: deployment
        uses: actions/deploy-pages@v4
```

### Typical Workflow

```
1. geek42 new                 Write a new post
2. geek42 lint .              Verify format
3. git add -A && git commit   Commit the new item
4. git push                   Publish (triggers site build)
```

## Reading Other People's News

### Adding Sources

Edit `geek42.toml` to add other news repositories:

```toml
[[sources]]
name = "gentoo"
url = "https://anongit.gentoo.org/git/data/glep42-news-gentoo.git"
branch = "master"

[[sources]]
name = "friend"
url = "https://github.com/friend/their-news.git"
branch = "main"

[[sources]]
name = "overlay"
url = "https://github.com/org/overlay-news.git"
branch = "main"
```

### Pulling and Reading in the Terminal

```sh
# Fetch all sources
geek42 pull

# List recent news from all sources
geek42 list

# Filter by source
geek42 list --source gentoo

# Read a specific item
geek42 read flexiblas-migration
```

The `list` command shows a Rich table with date, title, source, and
item ID. The `read` command renders a single item with full metadata
in a Rich panel.

### Building an Aggregated Site

When you run `geek42 build`, all sources are merged into a single
static site, sorted by date. Each post shows its source label so
readers can see where it came from. The RSS and Atom feeds include
items from all sources.

This means you can build a personal news aggregator that combines:
- Your own blog posts
- Official Gentoo news
- Overlay or project news from other repos

All in one static site with one RSS feed.

### No eselect Required

Unlike the traditional Gentoo workflow where `eselect news` reads
items from `/var/db/repos/*/metadata/news/`, geek42 works directly
with git repositories. This means:

- You can read news without being root
- You can read news from repos you don't have synced as overlays
- You can aggregate news from multiple sources
- You get a web-readable version with feeds

### Comparison with eselect news

| Feature | eselect news | geek42 |
|---------|--------------|--------|
| Read in terminal | Yes | Yes (`list`, `read`) |
| Web output | No | Yes (static site) |
| RSS/Atom | No | Yes |
| Multiple sources | Via repos only | Any git URL |
| Requires root | For portage repos | No |
| Markdown export | No | Yes |
| Linting | No | Yes |
| Compose/revise | No | Yes |
| Display-If filtering | Yes (automatic) | Shown as metadata |
