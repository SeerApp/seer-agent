"""seer-agent plugin bootstrap."""

from __future__ import annotations

import logging

from .handlers.commands import handle_slash
from .handlers.hooks import on_pre_llm_call, on_pre_tool_call
from .register import register_tools
from .types import SeerPluginContext

logger = logging.getLogger(__name__)


def register(ctx: SeerPluginContext) -> None:
    """Hermes plugin entrypoint."""
    logger.info("seer-agent plugin loaded")
    ctx.register_command(
        "seer-agent",
        handler=lambda raw_args: handle_slash(raw_args, ctx=ctx),
        description="Install and inspect Seer persona in SOUL.md.",
    )
    register_tools(ctx)
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
