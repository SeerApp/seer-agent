"""Filesystem paths for the seer-agent package."""

from __future__ import annotations

from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent


def package_dir() -> Path:
    """Directory containing package code and bundled data (personas, JSON, etc.)."""
    return _PKG_DIR
