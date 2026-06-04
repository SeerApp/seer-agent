"""Tests for home.resolve_hermes_home and home.resolve_display_home."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


def _empty_hermes_constants_module() -> types.ModuleType:
    """Module that makes ``from hermes_constants import …`` fail."""
    return types.ModuleType("hermes_constants")


class TestResolveHermesHome:
    def test_uses_get_hermes_home_when_available(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = Path("/var/hermes-profile")
        mod = types.ModuleType("hermes_constants")
        mod.get_hermes_home = lambda: expected
        monkeypatch.setitem(sys.modules, "hermes_constants", mod)
        assert home.resolve_hermes_home() == expected

    def test_falls_back_to_hermes_home_env(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _empty_hermes_constants_module())
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "custom-hermes"))
        assert home.resolve_hermes_home() == (tmp_path / "custom-hermes").resolve()

    def test_falls_back_to_default_dot_hermes(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _empty_hermes_constants_module())
        monkeypatch.delenv("HERMES_HOME", raising=False)
        fake_home = Path("/fake-user-home")
        with patch.object(Path, "home", return_value=fake_home):
            assert home.resolve_hermes_home() == fake_home / ".hermes"

    def test_falls_back_when_get_hermes_home_raises(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        mod = types.ModuleType("hermes_constants")

        def _boom() -> Path:
            raise RuntimeError("hermes unavailable")

        mod.get_hermes_home = _boom
        monkeypatch.setitem(sys.modules, "hermes_constants", mod)
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "env-fallback"))
        assert home.resolve_hermes_home() == (tmp_path / "env-fallback").resolve()


class TestResolveDisplayHome:
    def test_uses_display_hermes_home_when_available(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mod = types.ModuleType("hermes_constants")
        mod.display_hermes_home = lambda: "~/.hermes/profiles/coder"
        monkeypatch.setitem(sys.modules, "hermes_constants", mod)
        assert home.resolve_display_home(Path("/ignored/path")) == "~/.hermes/profiles/coder"

    def test_falls_back_to_str_home(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _empty_hermes_constants_module())
        path = Path("/some/hermes/home")
        assert home.resolve_display_home(path) == str(path)

    def test_falls_back_when_display_hermes_home_raises(
        self, home: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mod = types.ModuleType("hermes_constants")

        def _boom() -> str:
            raise RuntimeError("display helper failed")

        mod.display_hermes_home = _boom
        monkeypatch.setitem(sys.modules, "hermes_constants", mod)
        path = Path("/fallback/display")
        assert home.resolve_display_home(path) == str(path)
