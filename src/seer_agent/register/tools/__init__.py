"""Tool registration helpers for seer-agent."""

from ...types import SeerPluginContext

from .get_available_codebases import NAME as GET_AVAILABLE_CODEBASES_NAME
from .get_available_codebases import handler as get_available_codebases_handler
from .get_available_codebases import schema as get_available_codebases_schema

from .is_codebase_available import NAME as IS_CODEBASE_AVAILABLE_NAME
from .is_codebase_available import handler as is_codebase_available_handler
from .is_codebase_available import schema as is_codebase_available_schema

from .get_recommended_tools import NAME as GET_RECOMMENDED_TOOLS_NAME
from .get_recommended_tools import handler as get_recommended_tools_handler
from .get_recommended_tools import schema as get_recommended_tools_schema

from .trace_with_seer import NAME as TRACE_WITH_SEER_NAME
from .trace_with_seer import handler as trace_with_seer_handler
from .trace_with_seer import schema as trace_with_seer_schema

TOOLSET_NAME = "seer_agent"


def register_tools(ctx: SeerPluginContext) -> None:
    ctx.register_tool(
        name=GET_AVAILABLE_CODEBASES_NAME,
        toolset=TOOLSET_NAME,
        schema=get_available_codebases_schema(),
        handler=lambda args, **kw: get_available_codebases_handler(),
        description=(
            "List known Solana codebases; clone catalog repos only under the seer-agent store path."
        ),
        emoji="📋",
    )

    ctx.register_tool(
        name=IS_CODEBASE_AVAILABLE_NAME,
        toolset=TOOLSET_NAME,
        schema=is_codebase_available_schema(),
        handler=lambda args, **kw: is_codebase_available_handler(codebase=args.get("codebase", "")),
        description=(
            "Check if a catalog codebase is cloned under the seer-agent store path."
        ),
        emoji="📚",
    )

    ctx.register_tool(
        name=GET_RECOMMENDED_TOOLS_NAME,
        toolset=TOOLSET_NAME,
        schema=get_recommended_tools_schema(),
        handler=lambda args, **kw: get_recommended_tools_handler(),
        description="List recommended Solana dev CLIs with check, install, and verify commands.",
        emoji="🛠",
    )

    ctx.register_tool(
        name=TRACE_WITH_SEER_NAME,
        toolset=TOOLSET_NAME,
        schema=trace_with_seer_schema(),
        handler=lambda args, **kw: trace_with_seer_handler(
            project_path=args.get("project_path", ""),
            api_key=args.get("api_key"),
            skip_build=bool(args.get("skip_build", False)),
            consent=bool(args.get("consent", True)),
            no_idl=bool(args.get("no_idl", False)),
            artifacts_path=args.get("artifacts_path"),
        ),
        description=(
            "Return a complete step-by-step plan for tracing Solana transactions through Seer: "
            "prerequisites, authentication, seer run, test commands, and dashboard link."
        ),
        emoji="🔍",
    )
