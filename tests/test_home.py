"""Tests for home.resolve_hermes_home and home.resolve_display_home."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from seer_agent.home import resolve_display_home, resolve_hermes_home


def _hermes_constants_stub(
    *,
    get_hermes_home: Callable[[], Path] | None = None,
    display_hermes_home: Callable[[], str] | None = None,
) -> types.ModuleType | SimpleNamespace:
    """Fake ``hermes_constants`` for ``sys.modules`` (empty module → import fails)."""
    attrs = {
        k: v
        for k, v in (
            ("get_hermes_home", get_hermes_home),
            ("display_hermes_home", display_hermes_home),
        )
        if v is not None
    }
    if not attrs:
        return types.ModuleType("hermes_constants")
    return SimpleNamespace(**attrs)


class TestResolveHermesHome:
    def test_uses_get_hermes_home_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = Path("/var/hermes-profile")
        monkeypatch.setitem(
            sys.modules,
            "hermes_constants",
            _hermes_constants_stub(get_hermes_home=lambda: expected),
        )
        assert resolve_hermes_home() == expected

    def test_falls_back_to_hermes_home_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _hermes_constants_stub())
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "custom-hermes"))
        assert resolve_hermes_home() == (tmp_path / "custom-hermes").resolve()

    def test_falls_back_to_default_dot_hermes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _hermes_constants_stub())
        monkeypatch.delenv("HERMES_HOME", raising=False)
        fake_home = Path("/fake-user-home")
        with patch.object(Path, "home", return_value=fake_home):
            assert resolve_hermes_home() == fake_home / ".hermes"

    def test_falls_back_when_get_hermes_home_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def _boom() -> Path:
            raise RuntimeError("hermes unavailable")

        monkeypatch.setitem(
            sys.modules,
            "hermes_constants",
            _hermes_constants_stub(get_hermes_home=_boom),
        )
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "env-fallback"))
        assert resolve_hermes_home() == (tmp_path / "env-fallback").resolve()


class TestResolveDisplayHome:
    def test_uses_display_hermes_home_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(
            sys.modules,
            "hermes_constants",
            _hermes_constants_stub(
                display_hermes_home=lambda: "~/.hermes/profiles/coder"
            ),
        )
        assert resolve_display_home(Path("/ignored/path")) == "~/.hermes/profiles/coder"

    def test_falls_back_to_str_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "hermes_constants", _hermes_constants_stub())
        path = Path("/some/hermes/home")
        assert resolve_display_home(path) == str(path)

    def test_falls_back_when_display_hermes_home_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom() -> str:
            raise RuntimeError("display helper failed")

        monkeypatch.setitem(
            sys.modules,
            "hermes_constants",
            _hermes_constants_stub(display_hermes_home=_boom),
        )
        path = Path("/fallback/display")
        assert resolve_display_home(path) == str(path)
