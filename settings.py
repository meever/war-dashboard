"""Application settings and one-time runtime bootstrap helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

APP_VERSION = "v2.0"

# Canonical path for local parquet data storage
DATA_DIR = Path(__file__).resolve().parent / "local_data"

CRACK_LOW_PERCENTILE = 5
CRACK_HIGH_PERCENTILE = 95
CRACK_DROP_ALERT_PCT = -15.0
INVENTORY_ALERT_ZSCORE = 2.0
TANKER_DROP_ALERT_PCT = -15.0

_LOGGING_CONFIGURED = False
_ENV_LOADED = False


def load_environment() -> None:
    """Load .env values once for the current process."""
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(override=True)
        _ENV_LOADED = True


def configure_logging() -> None:
    """Configure application logging once."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _LOGGING_CONFIGURED = True


def bootstrap_runtime() -> Path:
    """Prepare environment variables, logging, and local data storage."""
    load_environment()
    configure_logging()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not os.access(DATA_DIR, os.W_OK):
        raise RuntimeError(f"Local data directory is not writable: {DATA_DIR}")
    return DATA_DIR