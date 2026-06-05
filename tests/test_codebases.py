"""Tests for codebase catalog and clone layout."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import seer_agent.codebases as codebases


class TestResolveCodebasesRoot:
    def test_under_hermes_home_by_default(self, tmp_path: Path) -> None:
        home = tmp_path / "profile"
        assert codebases.resolve_codebases_root(home=home) == (
            home / "seer-agent" / "codebases"
        ).resolve()

    def test_seer_codebases_root_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        custom = tmp_path / "shared-repos"
        monkeypatch.setenv("SEER_CODEBASES_ROOT", str(custom))
        assert codebases.resolve_codebases_root(home=tmp_path / "ignored") == custom.resolve()


class TestLoadCatalog:
    def test_catalog_is_nonempty_and_entries_are_well_formed(self) -> None:
        catalog = codebases.load_catalog()
        assert catalog
        for name, entry in catalog.items():
            assert name.strip()
            git = entry["git"]
            assert git.startswith("https://")
            assert entry["description"].strip()
            assert isinstance(entry["docs"], str)

    def test_catalog_summaries_match_catalog(self) -> None:
        catalog = codebases.load_catalog()
        summaries = codebases.catalog_summaries()
        assert len(summaries) == len(catalog)
        assert {summary["name"] for summary in summaries} == set(catalog)
        for summary in summaries:
            entry = catalog[summary["name"]]
            assert summary["description"] == entry["description"]
            assert summary["docs"] == entry["docs"]


class TestIsCodebaseAvailable:
    def test_false_when_directory_missing(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        name = codebases.catalog_names()[0]
        assert codebases.is_codebase_available(name, home=home) is False

    def test_false_for_unknown_name(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        assert codebases.is_codebase_available("not-in-catalog", home=home) is False

    def test_true_when_git_repo_present(self, tmp_path: Path) -> None:
        home = tmp_path / "hermes"
        name = codebases.catalog_names()[0]
        clone = codebases.codebase_local_path(name, home=home)
        clone.mkdir(parents=True)
        with patch.object(codebases, "is_git_repo", return_value=True):
            assert codebases.is_codebase_available(name, home=home) is True


class TestGetAvailableCodebasesHandler:
    def test_returns_catalog_summaries(self) -> None:
        from seer_agent.register.tools.get_available_codebases import handler

        data = json.loads(handler())
        assert data["success"] is True
        assert data["codebases"] == codebases.catalog_summaries()
        assert data["codebases"]


class TestIsCodebaseAvailableHandler:
    def test_unknown_codebase(self) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        raw = handler("missing")
        data = json.loads(raw)
        assert data["success"] is False
        assert data["known_codebases"] == codebases.catalog_names()

    def test_known_but_not_cloned(self, tmp_path: Path) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        home = tmp_path / "hermes"
        name = codebases.catalog_names()[0]
        with patch.object(codebases, "resolve_hermes_home", return_value=home):
            raw = handler(name)
        data = json.loads(raw)
        assert data["success"] is True
        assert data["codebase"] == name
        assert data["available"] is False
        assert data["path"] == str(codebases.codebase_local_path(name, home=home))

    def test_known_and_cloned(self, tmp_path: Path) -> None:
        from seer_agent.register.tools.is_codebase_available import handler

        home = tmp_path / "hermes"
        name = codebases.catalog_names()[0]
        with (
            patch.object(codebases, "resolve_hermes_home", return_value=home),
            patch.object(codebases, "is_git_repo", return_value=True),
        ):
            raw = handler(name)
        data = json.loads(raw)
        assert data["available"] is True
