"""Tests for core.codebase_store."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from seer_agent.core import codebase_store


class TestResolveCodebasesRoot:
    def test_under_hermes_home_by_default(self, tmp_path: Path) -> None:
        home = tmp_path / "profile"
        assert codebase_store.resolve_codebases_root(home=home) == (
            home / "seer-agent" / "codebases"
        ).resolve()

    def test_seer_codebases_root_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        custom = tmp_path / "shared-repos"
        monkeypatch.setenv("SEER_CODEBASES_ROOT", str(custom))
        assert codebase_store.resolve_codebases_root(home=tmp_path / "ignored") == custom.resolve()


class TestLoadCatalog:
    def test_reads_bundled_codebases_json(self) -> None:
        catalog = codebase_store.load_catalog()
        assert "agave" in catalog
        assert catalog["agave"].startswith("https://")


class TestIsAvailable:
    def test_false_when_directory_missing(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        assert codebase_store.is_available("agave", home=home) is False

    def test_false_for_unknown_name(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        assert codebase_store.is_available("not-in-catalog", home=home) is False

    def test_true_when_git_repo_present(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        clone = codebase_store.local_path("agave", home=home)
        clone.mkdir(parents=True)
        with patch.object(codebase_store, "is_git_repo", return_value=True):
            assert codebase_store.is_available("agave", home=home) is True


class TestGetAvailableCodebasesHandler:
    def test_returns_catalog_keys(self) -> None:
        from seer_agent.register.tools.get_available_codebases import handler

        data = json.loads(handler())
        assert data["success"] is True
        assert data["codebases"] == codebase_store.catalog_names()
        assert "agave" in data["codebases"]


class TestIsCodebaseAvailableHandler:
    def test_unknown_codebase(self) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        raw = handler("missing")
        data = json.loads(raw)
        assert data["success"] is False
        assert "agave" in data["known_codebases"]

    def test_known_but_not_cloned(self, tmp_path: Path) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        home = tmp_path / "hermes"
        with patch.object(codebase_store, "resolve_hermes_home", return_value=home):
            raw = handler("agave")
        data = json.loads(raw)
        assert data["success"] is True
        assert data["codebase"] == "agave"
        assert data["available"] is False
        assert data["path"] == str(codebase_store.local_path("agave", home=home))

    def test_known_and_cloned(self, tmp_path: Path) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        home = tmp_path / "hermes"
        with (
            patch.object(codebase_store, "resolve_hermes_home", return_value=home),
            patch.object(codebase_store, "is_git_repo", return_value=True),
        ):
            raw = handler("agave")
        data = json.loads(raw)
        assert data["available"] is True
