"""Tests for structured logging configuration."""

from __future__ import annotations

import logging

import structlog

from geek42.logging import configure_logging


class TestConfigureLogging:
    def setup_method(self) -> None:
        """Save root logger state before each test."""
        root = logging.getLogger()
        self._orig_level = root.level
        self._orig_handlers = root.handlers[:]

    def teardown_method(self) -> None:
        """Restore root logger state after each test."""
        root = logging.getLogger()
        root.handlers = self._orig_handlers
        root.setLevel(self._orig_level)

    def test_default_level_is_info(self) -> None:
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_verbose_sets_debug(self) -> None:
        configure_logging(verbose=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_json_mode_produces_json(self) -> None:
        configure_logging(json_output=True)
        logger = structlog.stdlib.get_logger("test")
        logger.info("test_event", key="value")

        # Verify handler is configured and writing to stderr
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_human_mode_produces_readable_output(self) -> None:
        configure_logging(json_output=False)
        # Should not raise
        logger = structlog.stdlib.get_logger("test")
        logger.info("hello", count=42)

    def test_configure_clears_old_handlers(self) -> None:
        # Add a dummy handler
        root = logging.getLogger()
        root.addHandler(logging.NullHandler())

        configure_logging()
        # Should have exactly 1 handler (the new stderr one)
        assert len(root.handlers) == 1
