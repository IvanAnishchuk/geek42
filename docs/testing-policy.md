# Testing and Coverage Policy

This document describes the testing expectations for geek42. It is
referenced by `CONTRIBUTING.md`, `SECURITY.md`, and the OpenSSF Best
Practices badge answers.

---

## New code must have tests

Every PR that adds or changes functionality must include tests.

- **New features**: add tests that exercise the happy path and at
  least one error path.
- **Bug fixes**: add a regression test that fails without the fix
  and passes with it.
- **Refactors**: existing tests should still pass. If behavior
  changes, update tests to match.

If a specific piece of code is genuinely untestable (e.g., it
delegates to an external tool like `gemato` and the test would
just be mocking), mark it with `# pragma: no cover` and add a
brief comment explaining why.

## Coverage rules

**Floor**: CI enforces a minimum coverage of **75%** via
`[tool.coverage.report] fail_under` in `pyproject.toml`. This is
a hard gate — the test job fails if coverage drops below it.

**No-regression on PRs**: the coverage comment action
(`py-cov-action/python-coverage-comment-action`) posts a diff on
every PR showing which lines are newly uncovered. Reviewers should
flag PRs that add significant uncovered code.

**Continuous improvement**: the floor should be raised over time as
coverage improves. When coverage consistently stays above a new
threshold for several releases, bump `fail_under` up.

**Pragmatic exceptions**:

- Code that only runs with external tools (`gemato`, `gpg`, `gh`)
  and is covered by integration tests rather than unit tests may
  use `# pragma: no cover`.
- Generated templates (`scaffold.py` string constants) don't need
  line-by-line coverage — the scaffold tests verify the output.
- Error-handling paths that require simulating system failures
  (disk full, permission denied) can be excluded if the effort to
  test them outweighs the risk.

## What we test

| Layer | What | How |
|-------|------|-----|
| Parser | GLEP 42 format 1.0 + 2.0, edge cases, error paths | Unit tests (`test_parser.py`) |
| Compose | Template generation, slug derivation, placement | Unit tests (`test_compose.py`) |
| CLI | Every command, option combinations, error exits | Typer `CliRunner` (`test_cli.py`) |
| Site | Pull, collect, build, feed generation | Integration tests (`test_site.py`) |
| Manifest | Generate + verify, gemato parity | Integration tests (`test_manifest.py`) |
| Linter | All diagnostic codes | Unit tests (in `test_cli.py` lint section) |
| Blog | Compile, index, stale cleanup | Unit tests (`test_cli.py` compile-blog) |

## Running tests

```sh
# Full suite with coverage
uv run pytest

# Single file
uv run pytest tests/test_parser.py -v

# Single test
uv run pytest tests/test_cli.py::test_new_creates_item -v

# Skip gemato tests (if not installed)
uv run pytest -k "not gemato"
```

## CI enforcement

- `Test (Python 3.13)` is a **required status check** in branch
  protection — PRs cannot merge if tests fail.
- Coverage comment posts on PRs where tests pass successfully,
  showing statement and branch coverage metrics, per-file diffs,
  and inline annotations on uncovered lines.
- `fail_under` is the automated floor; reviewer judgment handles
  the rest.

## Evidence of adherence

This policy is actively enforced. Recent PRs demonstrate compliance:

- PR #124 (`download_artifacts.py`): 79 tests, 100% branch coverage
  on all new modules.
- PR #126 (`download_proofs.py`): 144 tests, 100% branch coverage
  on all pyscv modules.
- PR #127 (coverage reporting): added branch coverage metrics and
  inline annotations to PR comments.

Every merged PR since project inception includes tests for new
functionality. The coverage floor is currently set at 75% and should
be raised as coverage stabilizes. PRs that decrease coverage are flagged
by the coverage comment action and must be justified during review.

## Branch coverage

Branch (conditional) coverage is tracked alongside statement coverage.
The coverage comment on PRs shows both metrics:

| Metric | Tracked | CI gate |
|--------|---------|---------|
| Statement coverage | Yes | `fail_under = 75` |
| Branch coverage | Yes | Reported, not gated (reviewer judgment) |
| Missing line annotations | Yes | Warnings on PR diff |

The `pyscv` package maintains 100% branch coverage. The `geek42`
package targets >80% with pragmatic exceptions for UI/external-tool
integration code.
