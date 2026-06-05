"""Tool registration helpers for seer-agent."""

from ..types import SeerPluginContext

from .tools.get_available_codebases import NAME as GET_AVAILABLE_CODEBASES_NAME
from .tools.get_available_codebases import handler as get_available_codebases_handler
from .tools.get_available_codebases import schema as get_available_codebases_schema
from .tools.is_codebase_available import NAME as IS_CODEBASE_AVAILABLE_NAME
from .tools.is_codebase_available import handler as is_codebase_available_handler
from .tools.is_codebase_available import schema as is_codebase_available_schema

TOOLSET_NAME = "seer_agent"


def register_tools(ctx: SeerPluginContext) -> None:
    ctx.register_tool(
        name=GET_AVAILABLE_CODEBASES_NAME,
        toolset=TOOLSET_NAME,
        schema=get_available_codebases_schema(),
        handler=lambda args, **kw: get_available_codebases_handler(),
        description="List known Solana codebase names from the catalog.",
        emoji="📋",
    )

    ctx.register_tool(
        name=IS_CODEBASE_AVAILABLE_NAME,
        toolset=TOOLSET_NAME,
        schema=is_codebase_available_schema(),
        handler=lambda args, **kw: is_codebase_available_handler(codebase=args.get("codebase", "")),
        description="Check if a known Solana codebase is available locally.",
        emoji="📚",
    )