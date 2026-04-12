---
name: uv.lock must be committed
description: User wants uv.lock tracked in git, not ignored
type: feedback
---

Never add uv.lock to .gitignore. It should be committed for reproducible builds.

**Why:** Lock files ensure deterministic installs across environments.
**How to apply:** When creating .gitignore for Python/uv projects, only ignore .venv/, never uv.lock.
