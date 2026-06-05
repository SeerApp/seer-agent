"""seer-agent-tools bundled skill."""

from __future__ import annotations

from pathlib import Path

NAME = "seer-agent-tools"
DESCRIPTION = "Quick context for well-known Solana codebases and CLIs."


def skill_path() -> Path:
    return Path(__file__).resolve().parent / "SKILL.md"
