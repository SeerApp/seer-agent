"""Tests for recommended CLI tool catalog."""

from __future__ import annotations

import json

import seer_agent.recommended as recommended


class TestLoadRecommendedTools:
    def test_reads_bundled_recommended_json(self) -> None:
        tools = recommended.load_recommended_tools()
        assert "solana" in tools
        assert tools["solana"]["check"] == "solana -V"
        assert "solana-install.solana.workers.dev" in tools["solana"]["download"]
        assert tools["solana"]["docs"] == "https://solana.com/docs/intro/installation"
        assert "anchor --version" in tools["solana"]["verify"]

    def test_recommended_tool_summaries(self) -> None:
        summaries = recommended.recommended_tool_summaries()
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
