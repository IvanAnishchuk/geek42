"""Custom exception hierarchy for geek42.

All exceptions raised intentionally by geek42 inherit from
:class:`Geek42Error`. This lets CLI code catch a single base type at
its boundary while internal code still throws specific subtypes for
precise handling and testing.

Conventions:

- Every subclass carries its full message in ``__init__`` (avoids
  TRY003 and keeps call sites terse).
- Subclasses expose the relevant attributes (``path``, ``header``,
  ``name``, ``title``) for programmatic inspection.
- The hierarchy is shallow — only group errors that truly share
  handling logic.
"""

from __future__ import annotations

from pathlib import Path


class Geek42Error(Exception):
    """Base class for all geek42 exceptions."""


# --------------------------------------------------------------------
# Parser errors
# --------------------------------------------------------------------


class ParseError(Geek42Error):
    """A GLEP 42 news file could not be parsed."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.reason = message


class MissingHeaderError(ParseError):
    """A required GLEP 42 header is missing from a news file."""

    def __init__(self, path: Path, header: str) -> None:
        super().__init__(path, f"missing required header {header!r}")
        self.header = header


class InvalidHeaderValueError(ParseError):
    """A header exists but its value could not be parsed."""

    def __init__(self, path: Path, header: str, value: str) -> None:
        super().__init__(path, f"invalid value {value!r} for header {header!r}")
        self.header = header
        self.value = value


# --------------------------------------------------------------------
# Compose / revise errors
# --------------------------------------------------------------------


class ComposeError(Geek42Error):
    """Base class for compose and revise errors."""


class EmptyTitleError(ComposeError):
    """The composed news item has an empty Title header."""

    def __init__(self) -> None:
        super().__init__("Title cannot be empty")


class SlugDerivationError(ComposeError):
    """A valid slug could not be derived from the title."""

    def __init__(self, title: str) -> None:
        super().__init__(f"cannot derive a valid slug from title: {title!r}")
        self.title = title


class ItemNotFoundError(ComposeError):
    """The requested news item could not be located in any source."""

    def __init__(self, query: str) -> None:
        super().__init__(f"no news item matching {query!r}")
        self.query = query


# --------------------------------------------------------------------
# Configuration errors
# --------------------------------------------------------------------


class ConfigError(Geek42Error):
    """Base class for configuration problems."""


class SourceNotFoundError(ConfigError):
    """A source name referenced on the CLI is not in the config."""

    def __init__(self, name: str) -> None:
        super().__init__(f"unknown source: {name!r}")
        self.name = name


class NoSourcesConfiguredError(ConfigError):
    """No sources are configured in geek42.toml."""

    def __init__(self) -> None:
        super().__init__("no sources configured in geek42.toml")


class SourceNotPulledError(ConfigError):
    """A source repository has not been cloned yet."""

    def __init__(self, name: str) -> None:
        super().__init__(f"source {name!r} has not been pulled; run 'geek42 pull' first")
        self.name = name


# --------------------------------------------------------------------
# System dependency errors
# --------------------------------------------------------------------


class SystemDependencyError(Geek42Error):
    """A required external tool is missing from the system."""


class GitNotFoundError(SystemDependencyError):
    """The git executable is not on PATH."""

    def __init__(self) -> None:
        super().__init__("git executable not found in PATH")


class GematoNotFoundError(SystemDependencyError):
    """The gemato executable is not on PATH."""

    def __init__(self) -> None:
        super().__init__("gemato not found in PATH (install with: pip install gemato)")


class EditorFailedError(ComposeError):
    """The user's editor exited with a non-zero status."""

    def __init__(self, editor: str, returncode: int) -> None:
        super().__init__(f"editor {editor!r} exited with code {returncode}")
        self.editor = editor
        self.returncode = returncode
