# syntax=docker/dockerfile:1.9
#
# Multi-stage build for geek42:
#   1. builder  — uses uv to produce a frozen, hash-verified venv
#   2. runtime  — minimal distroless-style image with the venv copied in
#
# Build:
#     docker build -t geek42:latest .
#
# Run:
#     docker run --rm -v "$PWD:/work" geek42:latest --help
#     docker run --rm -v "$PWD:/work" geek42:latest build
#
# The image runs as a non-root user and writes only to /work.

ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.5.11
ARG DEBIAN_SUITE=slim-bookworm

# ============================================================
# Stage 1: builder
# ============================================================
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-${DEBIAN_SUITE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src

# Install git (needed at runtime for pull_source) into a well-known location
# so we can copy a minimal version into the final image.
RUN apt-get update \
 && apt-get install --no-install-recommends -y git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# First, sync dependencies (cached layer) — only copy lockfile + pyproject.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync \
    --frozen \
    --no-install-project \
    --no-dev

# Then copy source and install the project itself.
COPY src ./src
COPY LICENSE.md CHANGELOG.md ./
RUN uv sync --frozen --no-dev

# ============================================================
# Stage 2: runtime
# ============================================================
FROM python:${PYTHON_VERSION}-${DEBIAN_SUITE} AS runtime

# OCI image labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
ARG VERSION=0.4.2a10
ARG REVISION=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="geek42" \
      org.opencontainers.image.description="Convert GLEP 42 Gentoo news repositories into static blogs" \
      org.opencontainers.image.url="https://github.com/IvanAnishchuk/geek42" \
      org.opencontainers.image.source="https://github.com/IvanAnishchuk/geek42" \
      org.opencontainers.image.documentation="https://github.com/IvanAnishchuk/geek42/blob/main/README.md" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="CC0-1.0" \
      org.opencontainers.image.vendor="geek42 contributors" \
      org.opencontainers.image.base.name="docker.io/library/python:${PYTHON_VERSION}-${DEBIAN_SUITE}"

# Install only the runtime dependencies (git for pull_source).
RUN apt-get update \
 && apt-get install --no-install-recommends -y git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

# Create a non-root user
RUN groupadd --system --gid 1000 geek42 \
 && useradd --system --uid 1000 --gid 1000 \
      --home-dir /home/geek42 --create-home \
      --shell /usr/sbin/nologin geek42

# Copy the pre-built venv from the builder stage
COPY --from=builder --chown=geek42:geek42 /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GEEK42_DATA_DIR=/work/.geek42 \
    GEEK42_OUTPUT_DIR=/work/_site

USER geek42
WORKDIR /work

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD geek42 --help >/dev/null 2>&1 || exit 1

ENTRYPOINT ["geek42"]
CMD ["--help"]
