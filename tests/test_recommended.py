"""Tests for recommended CLI tool catalog."""

from __future__ import annotations

import json

import seer_agent.recommended as recommended


class TestLoadRecommendedTools:
    def test_reads_bundled_recommended_json(self) -> None:
        tools = recommended.load_recommended_tools()
        assert set(tools) == {
            "solana",
            "anchor",
            "surfpool",
            "rust",
            "node",
            "yarn",
            "jq",
        }
        assert tools["solana"]["check"] == "solana -V"
        assert "solana-install.solana.workers.dev" in tools["solana"]["download"]
        assert tools["anchor"]["check"] == "anchor --version"
        assert "solana-foundation/anchor" in tools["anchor"]["download"]
        assert tools["surfpool"]["description"]
        assert tools["jq"]["check"] == "jq --version"

    def test_recommended_tool_summaries(self) -> None:
        summaries = recommended.recommended_tool_summaries()
        assert len(summaries) == 7
        solana = next(item for item in summaries if item["name"] == "solana")
        assert solana["description"]
        assert solana["check"] == "solana -V"


class TestGetRecommendedToolsHandler:
    def test_returns_tool_summaries(self) -> None:
        from seer_agent.register.tools.get_recommended_tools import handler

        data = json.loads(handler())
        assert data["success"] is True
        assert data["tools"] == recommended.recommended_tool_summaries()
        assert any(item["name"] == "solana" for item in data["tools"])
