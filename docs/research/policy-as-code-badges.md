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

```text
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

## OSPS Security Baseline alignment

The [OSPS Security Baseline](https://github.com/ossf/security-baseline)
is an OpenSSF project that defines machine-readable security requirements
in YAML (Gemara Layer 2 schema). It has **three maturity levels** and
**eight control families**, each mapping to multiple frameworks including
the OpenSSF Best Practices Badge (BPB).

### Maturity levels

| Level | Applies to | Rough BPB equivalent |
|-------|-----------|---------------------|
| ML1 | Any project, any # of maintainers | Passing |
| ML2 | Code project, 2+ maintainers, some users | Silver |
| ML3 | Code project, large user base | Gold |

### Control families vs BPB categories

| OSPS Family | BPB Category | Overlap |
|-------------|-------------|---------|
| AC (Access Control) | Security | MFA, branch protection, CI permissions |
| BR (Build & Release) | Change Control + Quality | Versioning, signing, HTTPS delivery, changelogs |
| DO (Documentation) | Basics + Quality | User guides, build instructions, provenance docs |
| GV (Governance) | Basics | Roles, contributions, discussions |
| LE (Legal) | Basics (FLOSS license) | DCO/CLA, license location |
| QA (Quality) | Quality + Analysis | Public source, dependencies, testing, code review |
| SA (Security Assessment) | Security | Design docs, threat modeling, security assessment |
| VM (Vulnerability Mgmt) | Reporting + Security | CVD policy, private reporting, SCA/SAST enforcement |

### Key differences from BPB

1. **Machine-readable**: OSPS is YAML with structured IDs (`OSPS-AC-01.01`),
   not a web form. This aligns perfectly with policy-as-code.
2. **Cross-framework mapping**: Each control maps to BPB, CRA, SSDF, CSF,
   SLSA, SAMM, PCI-DSS, NIST 800-161. One policy file could satisfy
   multiple compliance frameworks.
3. **Actionable enforcement**: OSPS requirements are more specific about
   *how* to enforce (e.g., "status checks MUST pass before merge") vs
   BPB's more general "SHOULD have CI."
4. **SBOM required at ML3**: BPB doesn't explicitly require SBOMs; OSPS
   QA-02 does at Level 3.
5. **VEX required at ML3**: OSPS VM-04.02 requires VEX documents for
   non-exploitable vulnerabilities — BPB has no equivalent.
6. **No coverage thresholds**: OSPS doesn't specify coverage percentages
   (BPB Silver requires 80% statement, 80% branch; Gold requires 90%).
7. **Dependency policy**: OSPS VM-05 requires documented remediation
   policy for SCA findings — more specific than BPB's general
   "fix known vulnerabilities."

### OSPS requirements not in BPB

| OSPS Control | Requirement | Notes |
|-------------|-------------|-------|
| QA-05 | No executables in version control | BPB doesn't check this |
| BR-01.03 | Prevent untrusted code from accessing CI credentials | More specific than BPB |
| BR-07.02 | Documented secrets management policy | BPB only checks for leaks |
| VM-04.02 | VEX documents for non-exploitable vulns | Not in BPB at all |
| VM-05.01-03 | Documented SCA remediation policy + enforcement | BPB just says "fix vulns" |
| VM-06.01-02 | Documented SAST remediation policy + enforcement | BPB just says "use static analysis" |
| DO-03 | Provenance verification instructions | Unique to OSPS |
| DO-04/05 | Support scope and security update duration | Not in BPB |
| SA-03.02 | Threat modeling and attack surface analysis | BPB has "assurance case" but less specific |

### BPB requirements not in OSPS

| BPB Criterion | Requirement | Notes |
|-------------|-------------|-------|
| `test_statement_coverage80/90` | 80%/90% statement coverage | OSPS has no coverage thresholds |
| `test_branch_coverage80` | 80% branch coverage | OSPS has no coverage thresholds |
| `crypto_*` (10+ criteria) | Detailed crypto requirements | OSPS covers crypto minimally |
| `bus_factor` | Bus factor >= 2 | OSPS ML2 requires 2+ maintainers (similar but different) |
| `reproducible_builds` | Bit-for-bit reproducible | OSPS doesn't require this |

### How this informs policy-as-code

The OSPS YAML structure is the closest existing thing to our
policy-as-code idea. A unified policy file could:

1. Map each OSPS control to a CI check + badge
2. Include BPB-specific criteria that OSPS doesn't cover (coverage
   thresholds, crypto checks)
3. Use the OSPS YAML schema as a base format
4. Generate both OSPS compliance reports and BPB form answers from
   the same source

The `baseline-compiler` tool already converts YAML to Markdown and
NIST OSCAL JSON. A similar compiler could produce shields.io badge
JSON and OpenSSF form update URLs.

### Current geek42 compliance with OSPS

| Level | Controls met | Controls unmet | Notes |
|-------|-------------|----------------|-------|
| ML1 | ~90% | AC-01 (MFA enforcement unclear), QA-05 (need to verify no binaries) | Most are met by existing setup |
| ML2 | ~60% | GV-01 (no GOVERNANCE.md), SA-01/02 (no design docs), DO-06/07 (no dep/build policy docs) | Need documentation work |
| ML3 | ~30% | QA-07 (no merge approval requirement), VM-04.02 (no VEX), VM-05/06 (no remediation policy), DO-03/04/05, GV-04 | Significant work needed |

## Next steps

1. Prototype: Python script that reads a policy TOML and generates
   badge JSON files from CI outputs (coverage.xml, ruff SARIF, etc.)
2. Evaluate adopting OSPS YAML schema as the base format instead of
   custom TOML — leverage existing tooling (`baseline-compiler`)
3. Map geek42's existing CI checks to OSPS control IDs
4. Integrate into `scripts/regen_badges.py` pattern
5. Consider as a standalone tool or pyscv extension
