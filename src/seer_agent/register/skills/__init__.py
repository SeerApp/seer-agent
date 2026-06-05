"""Skill registration helpers for seer-agent."""

from ...types import SeerPluginContext

from .seer_agent_tools import DESCRIPTION as SEER_AGENT_TOOLS_DESCRIPTION
from .seer_agent_tools import NAME as SEER_AGENT_TOOLS_NAME
from .seer_agent_tools import skill_path as seer_agent_tools_skill_path


def register_skills(ctx: SeerPluginContext) -> None:
    ctx.register_skill(
        SEER_AGENT_TOOLS_NAME,
        seer_agent_tools_skill_path(),
        description=SEER_AGENT_TOOLS_DESCRIPTION,
    )
