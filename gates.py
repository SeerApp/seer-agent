"""Gate evaluation helpers for seer-agent hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional


def is_seer_routed_delegate(args: Optional[dict]) -> bool:
    if not isinstance(args, dict):
        return False
    meta = args.get("meta")
    if not isinstance(meta, dict):
        return False
    source = str(meta.get("source", "")).strip().lower()
    return source == "seer-agent"


def evaluate_business_gate(tool_name: str, business_gate: Optional[dict], allowed_tools: set[str]) -> Optional[dict]:
    if business_gate and not business_gate.get("satisfied"):
        if tool_name not in allowed_tools:
            return {
                "action": "block",
                "message": (
                    "seer-agent business gate: business requirements are not yet defined. "
                    "Before any technical planning or implementation, call `clarify` to gather "
                    "business intent and then call `seer_set_business_brief` with the required fields."
                ),
            }
    return None


def evaluate_merge_policy(tool_name: str, args: Optional[dict], active_persona: str, project_manager_name: str) -> Optional[dict]:
    if tool_name != "terminal" or not isinstance(args, dict):
        return None
    command = str(args.get("command", "") or "").lower()
    if "git merge" in command and (" main" in command or " master" in command):
        if active_persona != project_manager_name:
            return {
                "action": "block",
                "message": "seer-agent merge policy: only Project Manager may merge into main/master.",
            }
    return None


def evaluate_scope_gate(
    *,
    tool_name: str,
    git_gate: Optional[dict],
    allowed_tools: set[str],
    persona_tools: set[str],
    normalize_allowed_paths: Callable[[list[str]], list[str]],
    get_task_binding: Callable[[Path, str], dict],
    update_allowed_paths: Callable[[list[str]], None],
    git_changed_files: Callable[[Path], list[str]],
    files_outside_scope: Callable[[list[str], list[str]], list[str]],
) -> Optional[dict]:
    if (
        tool_name in allowed_tools
        or tool_name in persona_tools
        or not git_gate
        or not git_gate.get("satisfied")
    ):
        return None
    repo_root = Path(str(git_gate.get("repo_root", ""))).resolve()
    branch = str(git_gate.get("branch", "") or "")
    allowed_paths = normalize_allowed_paths(list(git_gate.get("allowed_paths", [])) if isinstance(git_gate, dict) else [])
    if repo_root.exists() and branch and not allowed_paths:
        binding = get_task_binding(repo_root, branch)
        allowed_paths = normalize_allowed_paths(binding.get("allowed_paths", []) if isinstance(binding, dict) else [])
        if allowed_paths:
            update_allowed_paths(allowed_paths)
    if not allowed_paths:
        return {
            "action": "block",
            "message": (
                "seer-agent scope gate: no strict task scope is bound to this branch. "
                "No strict task scope is bound to this branch."
            ),
        }
    dirty_files = git_changed_files(repo_root) if repo_root.exists() else []
    out_of_scope = files_outside_scope(dirty_files, allowed_paths)
    if out_of_scope:
        return {
            "action": "block",
            "message": (
                "seer-agent scope gate: branch contains out-of-scope file changes. "
                "Finalize or move work to the correct branch. "
                f"Out-of-scope files: {', '.join(out_of_scope[:5])}"
            ),
        }
    return None


def evaluate_precision_gate(
    *,
    tool_name: str,
    precision_gate: Optional[dict],
    allowed_tools: set[str],
    mark_clarified: Callable[[], None],
) -> Optional[dict]:
    if not precision_gate or precision_gate.get("satisfied"):
        return None
    if tool_name not in allowed_tools:
        return {
            "action": "block",
            "message": (
                "seer-agent precision gate: request is too vague for execution. "
                "First ask focused clarifying questions via the clarify tool."
            ),
        }
    if tool_name == "clarify":
        mark_clarified()
    return None


def evaluate_ambiguity_gate(
    *,
    tool_name: str,
    args: Optional[dict],
    ambiguity_gate: Optional[dict],
    mark_clarified: Callable[[], None],
    mark_decision_resolved: Callable[[Path, str, str], None],
) -> Optional[dict]:
    if not ambiguity_gate or ambiguity_gate.get("satisfied"):
        return None
    if tool_name != "clarify":
        return {
            "action": "block",
            "message": (
                "seer-agent ambiguity gate: multiple valid paths are possible. "
                "Ask the user to choose via `clarify` before proceeding."
            ),
        }
    mark_clarified()
    repo_root = None
    if isinstance(ambiguity_gate, dict):
        repo_raw = str(ambiguity_gate.get("repo_root", "") or "").strip()
        if repo_raw:
            repo_root = Path(repo_raw)
    if repo_root and repo_root.exists():
        topic = str(ambiguity_gate.get("topic", "") if isinstance(ambiguity_gate, dict) else "").strip()
        if topic:
            resolution = ""
            if isinstance(args, dict):
                resolution = str(args.get("answer", "") or args.get("response", "") or "").strip()
            mark_decision_resolved(repo_root, topic, resolution or "confirmed via clarify")
    return None
