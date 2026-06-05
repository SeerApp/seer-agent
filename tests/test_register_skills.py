"""Tests for skill registration."""

from __future__ import annotations

from unittest.mock import MagicMock

from seer_agent.register.skills import register_skills
from seer_agent.register.skills.seer_agent_tools import (
    DESCRIPTION,
    NAME,
    skill_path,
)


class TestRegisterSkills:
    def test_registers_seer_agent_tools_skill(self) -> None:
        ctx = MagicMock()
        register_skills(ctx)
        ctx.register_skill.assert_called_once_with(
            NAME,
            skill_path(),
            description=DESCRIPTION,
        )

    def test_skill_md_exists(self) -> None:
        path = skill_path()
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "seer-agent store" in text
        assert "get_available_codebases" in text
