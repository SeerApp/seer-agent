"""Hook entrypoints delegating into policy handlers with shared state."""

from __future__ import annotations

from typing import Any

from .policy_engine import handle_pre_llm_call, handle_pre_tool_call
from ..router import PROJECT_MANAGER
from ..core import state
from ..core import operations
from ..types import PreLlmCallHookResult, PreToolCallHookResult, ToolArgs


def on_pre_tool_call(
    *,
    tool_name: str = "",
    args: ToolArgs | None = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    **_: Any,
) -> PreToolCallHookResult:
    return handle_pre_tool_call(
        tool_name=tool_name,
        args=args,
        task_id=task_id,
        session_id=session_id,
        lock=state.GATE_LOCK,
        business_gate_map=state.BUSINESS_GATE,
        git_gate_map=state.GIT_GATE,
        precision_gate_map=state.PRECISION_GATE,
        ambiguity_gate_map=state.AMBIGUITY_GATE,
        active_persona_map=state.ACTIVE_PERSONA,
        allowed_tools=state.GATE_ALLOWED_TOOLS,
        project_manager_name=PROJECT_MANAGER,
        normalize_allowed_paths=operations.normalize_allowed_paths,
        get_task_binding=operations.load_task_binding,
        git_changed_files=operations.git_changed_files,
        files_outside_scope=operations.files_outside_scope,
        mark_decision_resolved=operations.mark_decision_resolved,
    )


def on_pre_llm_call(
    *,
    user_message: str = "",
    task_id: str = "",
    session_id: str = "",
    **_: Any,
) -> PreLlmCallHookResult:
    return handle_pre_llm_call(
        user_message=user_message,
        task_id=task_id,
        session_id=session_id,
        auto_route_keywords=state.AUTO_ROUTE_KEYWORDS,
        resolve_repo_business_context=lambda: operations.resolve_repo_business_context(),
        resolve_repo_dir=lambda: operations.resolve_repo_dir(""),
        git_repo_root_from=operations.git_repo_root_from,
        sync_active_branch_gate=operations.sync_active_branch_gate,
        is_decision_resolved=operations.is_decision_resolved,
        lock=state.GATE_LOCK,
        business_gate_map=state.BUSINESS_GATE,
        business_brief_map=state.BUSINESS_BRIEF,
        precision_gate_map=state.PRECISION_GATE,
        ambiguity_gate_map=state.AMBIGUITY_GATE,
        git_gate_map=state.GIT_GATE,
    )

