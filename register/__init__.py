"""Tool registration helpers for seer-agent."""

from ..types import SeerPluginContext

from .tools.is_codebase_available import NAME as IS_CODEBASE_AVAILABLE_NAME
from .tools.is_codebase_available import schema as is_codebase_available_schema
from .tools.is_codebase_available import handler as is_codebase_available_handler

TOOLSET_NAME="seer_agent"

def register_tools(ctx: SeerPluginContext) -> None:
    ctx.register_tool(
        name=IS_CODEBASE_AVAILABLE_NAME,
        toolset=TOOLSET_NAME,
        schema=is_codebase_available_schema,
        handler=lambda args, **kw: is_codebase_available_handler(codebase=args.get("codebase", "")),
        description="Check if a known Solana codebase is available locally.",
        emoji="📚",
    )