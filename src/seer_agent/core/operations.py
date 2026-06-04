"""Core operational helpers for seer-agent behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..router import FEATURE_DEVELOPER, PRINCIPAL_ENGINEER, PROJECT_MANAGER, build_delegate_payload_for_persona
from ..runtime_utils import extract_brief_from_docs, git_repo_root_from, resolve_repo_dir, run_cmd
from ..storage import (
    branch_policy_path,
    business_brief_store_path,
    decision_policy_path,
    load_branch_policy,
    load_decision_policy,
    load_persisted_business_brief,
    load_task_policy,
    save_json,
    task_policy_path,
)
from . import state


def normalize_allowed_paths(allowed_paths: list[str]) -> list[str]:
    norm: list[str] = []
    for raw in allowed_paths:
        if not isinstance(raw, str):
            continue
        p = raw.strip().lstrip("./")
        if not p:
            continue
        if p == "*":
            p = "**"
        norm.append(p)
    unique: list[str] = []
    seen = set()
    for p in norm:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def _task_policy_path(repo_root: Path) -> Path:
    return task_policy_path(repo_root, state.BUSINESS_BRIEF_STORE_DIR, state.TASK_POLICY_STORE_FILE)


def _decision_policy_path(repo_root: Path) -> Path:
    return decision_policy_path(repo_root, state.BUSINESS_BRIEF_STORE_DIR, state.DECISION_POLICY_STORE_FILE)


def _branch_policy_path(repo_root: Path) -> Path:
    return branch_policy_path(repo_root, state.BUSINESS_BRIEF_STORE_DIR, state.BRANCH_POLICY_STORE_FILE)


def _business_brief_path(repo_root: Path) -> Path:
    return business_brief_store_path(repo_root, state.BUSINESS_BRIEF_STORE_DIR, state.BUSINESS_BRIEF_STORE_FILE)


def load_task_binding(repo_root: Path, branch: str) -> dict:
    policy = load_task_policy(_task_policy_path(repo_root))
    entry = policy.get("branches", {}).get(branch, {})
    return entry if isinstance(entry, dict) else {}


def save_task_binding(repo_root: Path, branch: str, task_key: str, branch_description: str, allowed_paths: list[str]) -> None:
    policy = load_task_policy(_task_policy_path(repo_root))
    branches = policy.setdefault("branches", {})
    branches[branch] = {
        "task_key": task_key.strip(),
        "description": branch_description.strip(),
        "allowed_paths": normalize_allowed_paths(allowed_paths),
    }
    save_json(_task_policy_path(repo_root), policy)


def git_changed_files(repo_root: Path) -> list[str]:
    code, out = run_cmd(["git", "status", "--porcelain"], repo_root)
    if code != 0:
        return []
    files: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            files.append(path)
    return files


def branch_intent(repo_root: Path, branch: str) -> str:
    policy = load_branch_policy(_branch_policy_path(repo_root))
    branches = policy.get("branches", {})
    entry = branches.get(branch, {})
    desc = entry.get("description", "") if isinstance(entry, dict) else ""
    return str(desc or "").strip()


def sync_active_branch_gate(gate_key: str) -> None:
    repo_root = git_repo_root_from(resolve_repo_dir(""))
    if repo_root is None:
        return
    code, branch = run_cmd(["git", "branch", "--show-current"], repo_root)
    if code != 0:
        return
    branch_name = (branch or "").strip()
    if not branch_name:
        return
    binding = load_task_binding(repo_root, branch_name)
    allowed_paths = normalize_allowed_paths(binding.get("allowed_paths", []) if isinstance(binding, dict) else [])
    if not allowed_paths:
        return
    with state.GATE_LOCK:
        state.GIT_GATE[gate_key] = {
            "satisfied": True,
            "repo_root": str(repo_root),
            "branch": branch_name,
            "branch_intent": branch_intent(repo_root, branch_name),
            "task_key": str(binding.get("task_key", "") if isinstance(binding, dict) else ""),
            "allowed_paths": allowed_paths,
            "conventional_commits": True,
        }


def files_outside_scope(files: list[str], allowed_paths: list[str]) -> list[str]:
    normalized = normalize_allowed_paths(allowed_paths)
    if not normalized:
        return files
    if "**" in normalized:
        return []
    outside: list[str] = []
    for f in files:
        fp = f.strip().lstrip("./")
        in_scope = False
        for scope in normalized:
            s = scope.rstrip("/")
            if scope.endswith("/"):
                if fp.startswith(s + "/") or fp == s:
                    in_scope = True
                    break
            else:
                if fp == s or fp.startswith(s + "/"):
                    in_scope = True
                    break
        if not in_scope:
            outside.append(fp)
    return outside


def mark_decision_resolved(repo_root: Path, topic: str, resolution: str = "") -> None:
    if not topic.strip():
        return
    policy = load_decision_policy(_decision_policy_path(repo_root))
    decisions = policy.setdefault("decisions", {})
    decisions[topic.strip()] = {"resolved": True, "resolution": (resolution or "confirmed via clarify").strip()}
    save_json(_decision_policy_path(repo_root), policy)


def is_decision_resolved(repo_root: Path, topic: str) -> bool:
    if not topic.strip():
        return False
    policy = load_decision_policy(_decision_policy_path(repo_root))
    entry = policy.get("decisions", {}).get(topic.strip(), {})
    return bool(isinstance(entry, dict) and entry.get("resolved"))


def resolve_repo_business_context(repo_path: str = "") -> tuple[bool, str]:
    repo_dir = resolve_repo_dir(repo_path)
    repo_root = git_repo_root_from(repo_dir)
    if repo_root is None:
        return False, "not-a-repo"
    if load_persisted_business_brief(_business_brief_path(repo_root)):
        return True, "persisted-brief"
    # fallback to docs markers
    from ..runtime_utils import repo_has_business_docs

    if repo_has_business_docs(repo_root, state.BUSINESS_DOC_GLOBS, state.BUSINESS_DOC_MARKERS):
        return True, "docs-detected"
    return False, "not-found"


def refresh_business_brief_from_docs(repo_path: str = "", task_id: str = "", session_id: str = "") -> str:
    gate_key = task_id or session_id or "default"
    repo_dir = resolve_repo_dir(repo_path)
    repo_root = git_repo_root_from(repo_dir)
    if repo_root is None:
        return json.dumps({"success": False, "error": "Not inside a git repository."})
    inferred = extract_brief_from_docs(repo_root, state.BUSINESS_DOC_GLOBS)
    if not inferred:
        from ..runtime_utils import repo_has_business_docs

        if repo_has_business_docs(repo_root, state.BUSINESS_DOC_GLOBS, state.BUSINESS_DOC_MARKERS):
            inferred = {field: "Defined in repository docs." for field in state.BUSINESS_BRIEF_FIELDS}
    if not inferred:
        return json.dumps(
            {
                "success": False,
                "error": "Could not infer business brief from repository docs.",
                "hint": "Add business fields to docs or call seer_set_business_brief directly.",
            }
        )
    save_json(_business_brief_path(repo_root), {"brief": inferred})
    with state.GATE_LOCK:
        state.BUSINESS_BRIEF[gate_key] = inferred
        state.BUSINESS_GATE[gate_key] = {"satisfied": True, "reason": "business brief refreshed from docs"}
    return json.dumps({"success": True, "message": "Business brief refreshed from repository docs and persisted.", "repo_root": str(repo_root), "brief": inferred})


def set_business_brief(
    *,
    objective: str,
    target_users: str,
    problem_statement: str,
    success_metrics: str,
    scope_in: str,
    scope_out: str,
    constraints: str,
    current_stage: str,
    task_id: str = "",
    session_id: str = "",
) -> str:
    gate_key = task_id or session_id or "default"
    repo_root = git_repo_root_from(resolve_repo_dir(""))
    required = {
        "objective": objective,
        "target_users": target_users,
        "problem_statement": problem_statement,
        "success_metrics": success_metrics,
        "scope_in": scope_in,
        "scope_out": scope_out,
        "constraints": constraints,
        "current_stage": current_stage,
    }
    missing = [k for k, v in required.items() if not isinstance(v, str) or not v.strip()]
    if missing:
        return json.dumps({"success": False, "error": "Missing required business brief fields.", "missing_fields": missing})
    brief = {k: v.strip() for k, v in required.items()}
    with state.GATE_LOCK:
        state.BUSINESS_BRIEF[gate_key] = brief
        state.BUSINESS_GATE[gate_key] = {"satisfied": True, "reason": "business brief captured"}
    if repo_root is not None:
        save_json(_business_brief_path(repo_root), {"brief": brief})
    return json.dumps({"success": True, "message": "Business brief captured.", "brief": brief})


def delegate_to_persona(persona: str, task: str, stage: str = "", ctx=None) -> str:
    if ctx is None:
        return json.dumps({"error": "Plugin context unavailable for delegation."})
    task_text = (task or "").strip()
    if not task_text:
        return json.dumps({"error": "task is required"})
    stage_name = stage.strip() if isinstance(stage, str) and stage.strip() else "execution"
    decision, payload = build_delegate_payload_for_persona(persona, task_text, stage=stage_name)
    sync_active_branch_gate("default")
    with state.GATE_LOCK:
        for gate in state.PRECISION_GATE.values():
            gate["satisfied"] = True
            gate["reason"] = f"{decision.persona} invoked"
        state.ACTIVE_PERSONA["default"] = decision.persona
    raw = ctx.dispatch_tool("delegate_task", payload)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None
    return json.dumps(
        {
            "success": True,
            "routed_persona": decision.persona,
            "routed_stage": decision.stage,
            "reason": decision.reason,
            "delegate_result": parsed if isinstance(parsed, dict) else raw,
        }
    )


def principal_engineer(task: str, stage: str = "planning", ctx=None) -> str:
    return delegate_to_persona(PRINCIPAL_ENGINEER, task=task, stage=stage, ctx=ctx)


def feature_developer(task: str, stage: str = "execution", ctx=None) -> str:
    return delegate_to_persona(FEATURE_DEVELOPER, task=task, stage=stage, ctx=ctx)


def project_manager(task: str, stage: str = "management", ctx=None) -> str:
    return delegate_to_persona(PROJECT_MANAGER, task=task, stage=stage, ctx=ctx)


def extract_task_session_ids(kwargs: dict) -> tuple[str, str]:
    return str(kwargs.get("task_id", "") or ""), str(kwargs.get("session_id", "") or "")

