"""Hermes plugin entry — keeps ``plugin.yaml`` + root ``__init__.py`` at install path."""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent
_SRC = _PLUGIN_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from seer_agent import register

__all__ = ["register"]
