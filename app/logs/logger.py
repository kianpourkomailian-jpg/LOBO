"""
logger.py
=========
A tiny wrapper around Python's standard logging.

For now this gives every module a consistently-formatted console logger.
Stage 6 will add the structured audit trail (CSV/JSON logs written to the
Drive logs area). Keeping this minimal avoids over-engineering early on.

Usage:
    from app.logs.logger import get_logger
    log = get_logger(__name__)
    log.info("something happened")
"""

import logging

from app.config import settings

_CONFIGURED = False


def _configure_root() -> None:
    """Set up the root logger format/level exactly once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger using the shared configuration."""
    _configure_root()
    return logging.getLogger(name)
