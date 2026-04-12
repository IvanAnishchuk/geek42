# Downstream packaging

This directory contains metadata for building native OS packages
from geek42 source. Each subdirectory targets a different
distribution:

| Path | Target | Tool |
|------|--------|------|
| `debian/` | Debian / Ubuntu `.deb` | `dpkg-buildpackage` / `sbuild` |
| `rpm/geek42.spec` | CentOS / RHEL / Fedora `.rpm` | `rpmbuild` / `mock` |
| `gentoo/app-text/geek42/` | Gentoo ebuild | `pkgdev manifest` + overlay |
| `../Dockerfile` | OCI container image | `docker build` / `podman build` |

The canonical distribution is **PyPI** (via `pip install geek42` or
`uv tool install geek42`). These packages are provided for users and
distro maintainers who prefer native package management.

---

## Debian / Ubuntu

The `debian/` directory is a standard Debian source package layout.

```sh
# From the repo root
cp -r packaging/debian .
dpkg-buildpackage -us -uc -b
```

The resulting `.deb` lands in the parent directory. Install with:

```sh
sudo dpkg -i ../geek42_0.4.2~a7-1_all.deb
```

### Maintainer notes

- The package is **arch: all** (pure Python).
- Depends on `git` at runtime for `geek42 pull`.
- Uses `pybuild-plugin-pyproject` with the hatchling backend.
- Tests run during build via `dh_auto_test`.

---

## CentOS / RHEL / Fedora

The `rpm/geek42.spec` file follows the
[Fedora Python packaging guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/)
and uses `pyproject-rpm-macros`.

```sh
# Using rpmbuild directly
rpmbuild -bs packaging/rpm/geek42.spec \
    --define "_sourcedir $PWD" \
    --define "_srcrpmdir $PWD/build"

# Or using mock for a clean chroot build
mock --buildsrpm --spec packaging/rpm/geek42.spec --sources $PWD
mock --rebuild build/geek42-0.4.2~a7-1.*.src.rpm
```

### Maintainer notes

- Requires `python3-hatchling` and `pyproject-rpm-macros`.
- Builds as `python3-geek42` with a `/usr/bin/geek42` entrypoint.
- Runtime requires `git`.

---

## Gentoo

The ebuilds at `gentoo/app-text/geek42/` are ready to be dropped
into any Gentoo overlay.

```sh
# Assuming you have a personal overlay at /var/db/repos/myoverlay
mkdir -p /var/db/repos/myoverlay/app-text/geek42
cp packaging/gentoo/app-text/geek42/*.ebuild \
   packaging/gentoo/app-text/geek42/metadata.xml \
   /var/db/repos/myoverlay/app-text/geek42/

cd /var/db/repos/myoverlay/app-text/geek42
pkgdev manifest
emerge --ask app-text/geek42
```

### Maintainer notes

- `EAPI=8`, uses `distutils-r1` with `DISTUTILS_USE_PEP517=hatchling`.
- Supports Python 3.13 and 3.14.
- Runtime depends on `dev-vcs/git`.
- Tests run via `distutils_enable_tests pytest`.
- Follows the Gentoo category `app-text` because geek42 primarily
  processes text-based news items. Consider `www-apps` as an
  alternative if the static-site angle dominates for your overlay.

---

## Docker / OCI container

See [`../Dockerfile`](../Dockerfile) in the repo root.

```sh
# Build
docker build \
    --build-arg VERSION=0.4.2a7 \
    --build-arg REVISION=$(git rev-parse HEAD) \
    --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    -t geek42:0.4.2a7 -t geek42:latest .

# Run (mounts current dir as /work inside the container)
docker run --rm -v "$PWD:/work" geek42:latest --help
docker run --rm -v "$PWD:/work" geek42:latest pull
docker run --rm -v "$PWD:/work" geek42:latest build
```

### Image properties

- **Base**: `python:3.13-slim-bookworm`
- **Builder**: `ghcr.io/astral-sh/uv:0.5.11-python3.13-slim-bookworm`
- **Multi-stage**: builder produces a venv, runtime copies it in
- **Non-root**: runs as uid 1000 user `geek42`
- **Minimal**: only adds `git` and `ca-certificates` on top of the
  slim Python image
- **OCI labels**: all standard annotations set for tooling
  (`org.opencontainers.image.*`)
- **Reproducible**: builds from `uv.lock` with `--frozen`, producing
  byte-identical venvs for the same lockfile
- **Healthcheck**: validates `geek42 --help` runs

The Dockerfile is suitable for publishing to GHCR or Docker Hub. For
signed image publishing, extend the release workflow with
`cosign sign` and `attest-build-provenance` for container digests.

---

## Updating packaging for a new release

When bumping the geek42 version:

1. Update `pyproject.toml` and `src/geek42/__init__.py`
2. Update `CHANGELOG.md`
3. Update `packaging/debian/changelog`
4. Update `Version:` in `packaging/rpm/geek42.spec`
5. Rename `packaging/gentoo/app-text/geek42/geek42-X.Y.Z.ebuild`
6. Update `ARG VERSION=X.Y.Z` in `Dockerfile`
7. Tag the commit and push — the release workflow publishes wheels,
   sdist, SLSA provenance, sigstore signatures, and the OCI image

All of the above is listed in the release runbook at
[`../docs/devops.md`](../docs/devops.md).
