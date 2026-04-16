"""PyscvConfig — supply-chain verification config from pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel


class PyscvConfig(BaseModel):
    """Supply-chain verification config from pyproject.toml [tool.pyscv]."""

    package_name: str
    version: str
    repo_slug: str
    tag_prefix: str = "v"
    release_workflow: str = "release.yml"
    oidc_issuer: str = "https://token.actions.githubusercontent.com"
    identity_template: str = ""
    use_testpypi: bool = False
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
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        project = data["project"]
        pyscv = data.get("tool", {}).get("pyscv", {})
        return cls(
            package_name=project["name"],
            version=project["version"],
            repo_slug=pyscv.get("repo-slug", ""),
            tag_prefix=pyscv.get("tag-prefix", "v"),
            release_workflow=pyscv.get("release-workflow", "release.yml"),
            oidc_issuer=pyscv.get("oidc-issuer", "https://token.actions.githubusercontent.com"),
            identity_template=pyscv.get("identity-template", ""),
            use_testpypi=pyscv.get("use-testpypi", False),
            dist_dir=path.parent / "dist",
        )
