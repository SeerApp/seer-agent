"""Shared typing helpers for seer-agent."""

from __future__ import annotations

from typing import Any, Callable, Protocol


JsonDict = dict[str, Any]
ToolArgs = dict[str, Any]
ToolHandler = Callable[..., str]


class SeerPluginContext(Protocol):
    """Hermes plugin context surface used by seer-agent."""

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
