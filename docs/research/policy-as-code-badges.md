# Research: Policy-as-Code with Auto-Generated Badges

**Date:** 2026-04-19
**Status:** Idea / Future exploration

## Concept

A policy document (TOML/YAML) where each key maps to an OpenSSF Best
Practices criterion (or similar compliance framework). Each entry
specifies:

- The criterion ID and description
- A threshold or boolean value (e.g., `coverage_floor = 75`)
- The CI workflow that verifies it
- The badge endpoint to generate

CI workflows read the policy file, verify the criterion is met, and
produce per-criterion badge JSON files. The policy file becomes a
self-verifying compliance manifest — if a badge is green, the
criterion is automated and passing.

## Example

```toml
[criteria.test_coverage]
id = "test_most"
description = "Test suite covers most of the code"
threshold = 75
metric = "statement_coverage_percent"
workflow = "test.yml"
badge = "badges/coverage.json"

[criteria.branch_coverage]
id = "test_branches"
description = "Branch coverage tracked and reported"
threshold = 60
metric = "branch_coverage_percent"
workflow = "test.yml"
badge = "badges/branch-coverage.json"

[criteria.new_code_coverage]
id = "tests_are_added"
description = "New code has adequate test coverage"
threshold = 90
metric = "diff_coverage_percent"
workflow = "coverage-diff.yml"
badge = "badges/new-code-coverage.json"

[criteria.static_analysis]
id = "static_analysis"
description = "Static analysis runs on every commit"
threshold = 0  # zero findings
metric = "ruff_findings_count"
workflow = "lint.yml"
badge = "badges/lint.json"

[criteria.security_scan]
id = "static_analysis_common_vulnerabilities"
description = "Security-focused static analysis"
threshold = 0
metric = "security_findings_count"
workflow = "security-lint.yml"
badge = "badges/security.json"
```

## Architecture

```
policy.toml
    ↓ (read by)
CI workflows (test.yml, lint.yml, etc.)
    ↓ (produce)
badges/*.json (shields.io endpoint format)
    ↓ (rendered in)
README.md badges
    ↓ (also feeds)
OpenSSF badge form (manual or API update)
```

## Benefits

- Single source of truth for compliance criteria + thresholds
- Badges reflect actual CI results, not self-reported claims
- Policy changes (raising thresholds) are tracked in git history
- Could auto-generate the OpenSSF badge form answers
- Reusable across projects — scaffold new projects with the same
  policy file and get the same badge infrastructure

## Challenges

- OpenSSF badge API doesn't support programmatic updates (form only)
- Need a workflow step that reads TOML and generates badge JSON
- Each criterion needs a different metric extraction method
- Some criteria are binary (Met/Unmet), others are thresholds
- Some criteria can't be automated (e.g., "developer knows secure design")

## Prior art

- Scorecard (OpenSSF) — automated checks, but fixed criteria
- AllStar (OpenSSF) — policy enforcement, but GitHub-specific
- Compliance-as-code (general concept in DevSecOps)
- OPA/Rego policies — infrastructure policy, different domain

## Next steps

1. Prototype: Python script that reads a policy TOML and generates
   badge JSON files from CI outputs (coverage.xml, ruff SARIF, etc.)
2. Integrate into `scripts/regen_badges.py` pattern
3. Consider as a standalone tool or pyscv extension
