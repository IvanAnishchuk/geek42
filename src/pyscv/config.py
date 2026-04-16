"""PyscvConfig — supply-chain verification config from pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PyscvConfig(BaseModel):
    """Supply-chain verification config from pyproject.toml [tool.pyscv]."""

    model_config = ConfigDict(populate_by_name=True)

    package_name: str
    version: str
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

    @classmethod
    def from_pyproject(cls, path: Path) -> PyscvConfig:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            project = data["project"]
        except FileNotFoundError as exc:
            msg = f"pyproject.toml not found: {path}"
            raise ValueError(msg) from exc
        except (tomllib.TOMLDecodeError, KeyError) as exc:
            msg = f"pyproject.toml missing required field: {exc}"
            raise ValueError(msg) from exc

        pyscv = data.get("tool", {}).get("pyscv", {})

        return cls(
            package_name=project["name"],
            version=project["version"],
            dist_dir=path.parent / "dist",
            **pyscv,
        )
