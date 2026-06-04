"""Pytest setup for seer-agent.

Load flat plugin modules (e.g. ``home.py``) by file path so we never put the
plugin root on ``sys.path`` — that would make pytest import ``__init__.py`` and
break relative imports in the plugin bootstrap.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def home() -> ModuleType:
    return _load_module("seer_agent_home", ROOT / "home.py")
