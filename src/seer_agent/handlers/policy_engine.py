"""Policy engine for pre-tool and pre-llm hook handling."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ..gates import (
    evaluate_ambiguity_gate,
    evaluate_business_gate,
    evaluate_merge_policy,
    evaluate_precision_gate,
    evaluate_scope_gate,
    is_seer_routed_delegate,
)
from ..heuristics import (
    extract_ambiguity_topic,
    looks_ambiguous_decision,
    looks_business_vague,
    looks_like_coding_request,
    looks_vague,
)


def _update_pre_llm_gates(
    *,
    gate_key: str,
    business_vague: bool,
    has_repo_business_context: bool,
    business_source: str,
    vague: bool,
    ambiguity_vague: bool,
    ambiguity_resolved: bool,
    ambiguity_topic: str,
    repo_root: Optional[Path],
    lock,
    business_gate: dict[str, dict[str, object]],
    business_brief: dict[str, dict[str, str]],
    precision_gate: dict[str, dict[str, object]],
    ambiguity_gate: dict[str, dict[str, object]],
    git_gate: dict[str, dict[str, object]],
) -> None:
    with lock:
        if business_vague:
            if has_repo_business_context:
                business_gate[gate_key] = {
                    "satisfied": True,
                    "reason": f"business context already present ({business_source})",
                }
            else:
                business_gate[gate_key] = {"satisfied": False, "reason": "missing business brief"}
        elif gate_key in business_gate and gate_key not in business_brief:
            if has_repo_business_context:
                business_gate[gate_key] = {
                    "satisfied": True,
                    "reason": f"business context already present ({business_source})",
                }
            else:
                business_gate[gate_key] = {"satisfied": False, "reason": "business brief required"}
        else:
            business_gate.pop(gate_key, None)

        if vague:
            precision_gate[gate_key] = {"satisfied": False, "reason": "vague prompt"}
        else:
            precision_gate.pop(gate_key, None)

        if ambiguity_vague and not ambiguity_resolved:
            ambiguity_gate[gate_key] = {
                "satisfied": False,
                "reason": "ambiguous decision path",
                "topic": ambiguity_topic,
                "repo_root": str(repo_root) if repo_root else "",
            }
        else:
            ambiguity_gate.pop(gate_key, None)

        if gate_key not in git_gate:
            git_gate[gate_key] = {"satisfied": False, "reason": "git workflow not prepared"}


def _build_pre_llm_policy_context(
    *,
    business_vague: bool,
    has_repo_business_context: bool,
    vague: bool,
    ambiguity_vague: bool,
    ambiguity_resolved: bool,
) -> str:
    if business_vague and not has_repo_business_context:
        return (
            "seer-agent strict business-first policy: this request is missing business intent. "
            "Your next action MUST be a single `clarify` tool call focused on business goals "
            "(objective, target users, problem statement, success metrics, in-scope/out-of-scope, constraints, stage). "
            "After clarification, call `seer_set_business_brief` with all required fields. "
            "Do not perform technical planning or implementation before the brief is captured."
        )
    if vague:
        return (
            "seer-agent strict policy: this coding request is vague. "
            "Your next action MUST be a single `clarify` tool call immediately. "
            "Do not produce free-form analysis, plans, or long reasoning before clarifying. "
            "Ask concise, high-leverage questions that pin down scope, constraints, success criteria, "
            "and the first deliverable. After clarify resolves ambiguity, delegate with "
            "`principal_engineer` for planning."
        )
    if ambiguity_vague and not ambiguity_resolved:
        return (
            "seer-agent decision policy: this request indicates multiple plausible implementation paths. "
            "Before choosing an approach, your next action MUST be a single `clarify` call that presents "
            "2-3 concrete options with trade-offs and asks the user to choose. "
            "Do not proceed with planning/execution until the user selects a direction."
        )
    return (
        "seer-agent workflow policy: choose the explicit persona tool for this work: "
        "`principal_engineer` for planning/refactor/evaluation, `feature_developer` for implementation, "
        "or `project_manager` for documentation/status/progress/branch lifecycle tasks. "
        "Feature Developer is responsible for creating new branches; only Project Manager may merge into main/master. "
        "Keep work aligned to active branch scope. "
        "Do not discuss internal workflow mechanics in user-facing responses unless explicitly asked."
    )


def handle_pre_tool_call(
    *,
    tool_name: str,
    args: Optional[dict],
    task_id: str,
    session_id: str,
    lock,
    business_gate_map: dict[str, dict[str, object]],
    git_gate_map: dict[str, dict[str, object]],
    precision_gate_map: dict[str, dict[str, object]],
    ambiguity_gate_map: dict[str, dict[str, object]],
    active_persona_map: dict[str, str],
    allowed_tools: set[str],
    project_manager_name: str,
    normalize_allowed_paths: Callable[[list[str]], list[str]],
    get_task_binding: Callable[[Path, str], dict],
    git_changed_files: Callable[[Path], list[str]],
    files_outside_scope: Callable[[list[str], list[str]], list[str]],
    mark_decision_resolved: Callable[[Path, str, str], None],
) -> Optional[dict]:
    gate_key = task_id or session_id or "default"
    with lock:
        business_gate = business_gate_map.get(gate_key)
        git_gate = git_gate_map.get(gate_key)
        precision_gate = precision_gate_map.get(gate_key)
        ambiguity_gate = ambiguity_gate_map.get(gate_key)
        active_persona = active_persona_map.get(gate_key) or active_persona_map.get("default", "")

    def _update_allowed_paths(allowed_paths: list[str]) -> None:
        with lock:
            if gate_key in git_gate_map:
                git_gate_map[gate_key]["allowed_paths"] = allowed_paths

    def _mark_precision_clarified() -> None:
        with lock:
            if gate_key in precision_gate_map:
                precision_gate_map[gate_key]["satisfied"] = True
                precision_gate_map[gate_key]["reason"] = "clarify invoked"

    def _mark_ambiguity_clarified() -> None:
        with lock:
            if gate_key in ambiguity_gate_map:
                ambiguity_gate_map[gate_key]["satisfied"] = True
                ambiguity_gate_map[gate_key]["reason"] = "clarify invoked for decision"

    gate_checks = (
        lambda: evaluate_business_gate(tool_name, business_gate, allowed_tools),
        lambda: evaluate_merge_policy(tool_name, args, active_persona, project_manager_name),
        lambda: evaluate_scope_gate(
            tool_name=tool_name,
            git_gate=git_gate,
            allowed_tools=allowed_tools,
            persona_tools={"principal_engineer", "feature_developer", "project_manager"},
            normalize_allowed_paths=normalize_allowed_paths,
            get_task_binding=get_task_binding,
            update_allowed_paths=_update_allowed_paths,
            git_changed_files=git_changed_files,
            files_outside_scope=files_outside_scope,
        ),
        lambda: evaluate_precision_gate(
            tool_name=tool_name,
            precision_gate=precision_gate,
            allowed_tools=allowed_tools,
            mark_clarified=_mark_precision_clarified,
        ),
        lambda: evaluate_ambiguity_gate(
            tool_name=tool_name,
            args=args,
            ambiguity_gate=ambiguity_gate,
            mark_clarified=_mark_ambiguity_clarified,
            mark_decision_resolved=mark_decision_resolved,
        ),
    )
    for check in gate_checks:
        outcome = check()
        if outcome:
            return outcome

    if tool_name != "delegate_task":
        return None
    if is_seer_routed_delegate(args):
        return None
    return {
        "action": "block",
        "message": (
            "seer-agent policy: do not call delegate_task directly. "
            "Use explicit persona tools: `principal_engineer`, `feature_developer`, or `project_manager`."
        ),
    }


def handle_pre_llm_call(
    *,
    user_message: str,
    task_id: str,
    session_id: str,
    auto_route_keywords: tuple[str, ...],
    resolve_repo_business_context: Callable[[], tuple[bool, str]],
    resolve_repo_dir: Callable[[], Path],
    git_repo_root_from: Callable[[Path], Optional[Path]],
    sync_active_branch_gate: Callable[[str], None],
    is_decision_resolved: Callable[[Path, str], bool],
    lock,
    business_gate_map: dict[str, dict[str, object]],
    business_brief_map: dict[str, dict[str, str]],
    precision_gate_map: dict[str, dict[str, object]],
    ambiguity_gate_map: dict[str, dict[str, object]],
    git_gate_map: dict[str, dict[str, object]],
) -> Optional[dict]:
    if not isinstance(user_message, str) or not user_message.strip():
        return None
    if not looks_like_coding_request(user_message, auto_route_keywords):
        return None

    gate_key = task_id or session_id or "default"
    sync_active_branch_gate(gate_key)

    vague = looks_vague(user_message)
    business_vague = looks_business_vague(user_message, auto_route_keywords)
    ambiguity_vague = looks_ambiguous_decision(user_message, auto_route_keywords)
    ambiguity_topic = extract_ambiguity_topic(user_message) if ambiguity_vague else ""
    has_repo_business_context, business_source = resolve_repo_business_context()
    repo_root = git_repo_root_from(resolve_repo_dir())
    ambiguity_resolved = bool(repo_root and ambiguity_topic and is_decision_resolved(repo_root, ambiguity_topic))

    _update_pre_llm_gates(
        gate_key=gate_key,
        business_vague=business_vague,
        has_repo_business_context=has_repo_business_context,
        business_source=business_source,
        vague=vague,
        ambiguity_vague=ambiguity_vague,
        ambiguity_resolved=ambiguity_resolved,
        ambiguity_topic=ambiguity_topic,
        repo_root=repo_root,
        lock=lock,
        business_gate=business_gate_map,
        business_brief=business_brief_map,
        precision_gate=precision_gate_map,
        ambiguity_gate=ambiguity_gate_map,
        git_gate=git_gate_map,
    )
    context = _build_pre_llm_policy_context(
        business_vague=business_vague,
        has_repo_business_context=has_repo_business_context,
        vague=vague,
        ambiguity_vague=ambiguity_vague,
        ambiguity_resolved=ambiguity_resolved,
    )
    return {"context": context}

