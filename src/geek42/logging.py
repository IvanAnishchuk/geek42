"""Structured logging configuration for geek42.

Provides two output modes:

- **Human** (default): coloured key=value lines via structlog's
  ``ConsoleRenderer``, suitable for interactive terminal use.
- **JSON** (``--json``): one JSON object per line, suitable for
  log aggregation, CI pipelines, and machine parsing.

Call :func:`configure_logging` once at CLI startup (in the Typer
callback) to wire up structlog for the rest of the process.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, json_output: bool = False, verbose: bool = False) -> None:
    """Configure structlog for CLI output.

    :param json_output: Emit JSON lines instead of human-readable output.
    :param verbose: Set log level to DEBUG (default is INFO).
    """
    level = logging.DEBUG if verbose else logging.INFO

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
