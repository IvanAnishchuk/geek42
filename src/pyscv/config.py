"""PyscvConfig — supply-chain verification config from pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PyscvConfig(BaseModel):
    """Supply-chain verification config.

    All fields default to empty/safe values. Config is built in phases:
    1. Load from [tool.pyscv] (all optional, kebab-case aliases)
    2. Augment with [project] fallbacks (name, version)
    3. Validate required fields before use

    This supports multiple config sources (TOML, CLI args, env vars)
    being layered before final validation.
    """

    model_config = ConfigDict(populate_by_name=True)

    package_name: str = Field(default="", alias="package-name")
    version: str = ""
    repo_slug: str = Field(default="", alias="repo-slug")
    tag_prefix: str = Field(default="v", alias="tag-prefix")
    release_workflow: str = Field(default="release.yml", alias="release-workflow")
    oidc_issuer: str = Field(
        default="https://token.actions.githubusercontent.com", alias="oidc-issuer"
    )
    identity_template: str = Field(default="", alias="identity-template")
    use_testpypi: bool = Field(default=False, alias="use-testpypi")
    dist_dir: Path = Path("dist")

    @property
    def pypi_base_url(self) -> str:
        return "https://test.pypi.org" if self.use_testpypi else "https://pypi.org"

    @property
    def pypi_label(self) -> str:
        return "TestPyPI" if self.use_testpypi else "PyPI"

    def tag(self, version: str | None = None) -> str:
        return f"{self.tag_prefix}{version or self.version}"

    def validate_required(self) -> None:
        """Validate that required fields are set. Call after all config sources applied."""
        missing = []
        if not self.package_name:
            missing.append("package_name")
        if not self.repo_slug:
            missing.append("repo_slug")
        if missing:
            msg = f"pyscv config missing required fields: {', '.join(missing)}"
            raise ValueError(msg)

    def augment_from_project(self, project: dict) -> PyscvConfig:
        """Fill in empty package_name and version from [project] section."""
        updates = {}
        if not self.package_name and project.get("name"):
            updates["package_name"] = project["name"]
        if not self.version and project.get("version"):
            updates["version"] = project["version"]
        if updates:
            return self.model_copy(update=updates)
        return self

    @classmethod
    def from_pyproject(cls, path: Path) -> PyscvConfig:
        """Load config from pyproject.toml, validate, and return."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            msg = f"pyproject.toml not found: {path}"
            raise ValueError(msg) from exc
        except tomllib.TOMLDecodeError as exc:
            msg = f"pyproject.toml is not valid TOML: {exc}"
            raise ValueError(msg) from exc

        pyscv = data.get("tool", {}).get("pyscv", {})
        config = cls(dist_dir=path.parent / "dist", **pyscv)

        project = data.get("project", {})
        config = config.augment_from_project(project)

        config.validate_required()
        return config
