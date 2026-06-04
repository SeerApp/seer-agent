"""Shared typing helpers for seer-agent."""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypedDict


JsonDict = dict[str, Any]
ToolArgs = dict[str, Any]
ToolHandler = Callable[..., str]
SlashCommandHandler = Callable[[str], str | None]


class HookBlockResult(TypedDict):
    action: str
    message: str


class HookContextResult(TypedDict):
    context: str


PreToolCallHookResult = HookBlockResult | None
PreLlmCallHookResult = HookContextResult | None


class SeerPluginContext(Protocol):
    """Hermes plugin context surface used by seer-agent."""

    def register_command(
        self,
        name: str,
        handler: SlashCommandHandler,
        description: str = "",
        args_hint: str = "",
    ) -> None: ...

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: JsonDict,
        handler: ToolHandler,
        check_fn: Callable[..., bool] | None = None,
        requires_env: list[str] | None = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        override: bool = False,
    ) -> None: ...

    def register_hook(
        self,
        hook_name: str,
        callback: Callable[..., Any],
    ) -> None: ...

    def dispatch_tool(
        self,
        tool_name: str,
        args: ToolArgs,
        **kwargs: Any,
    ) -> str: ...
