"""Routing logic for Seer subagent personas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PRINCIPAL_ENGINEER = "principal_engineer"
FEATURE_DEVELOPER = "feature_developer"
PROJECT_MANAGER = "project_manager"

PRINCIPAL_STAGES = {"planning", "refactor", "evaluation"}


@dataclass
class RouteDecision:
    persona: str
    stage: str
    reason: str
    role: str
    toolsets: list[str]


def _role_for_persona(persona: str) -> str:
    if persona in {PRINCIPAL_ENGINEER, PROJECT_MANAGER}:
        return "orchestrator"
    return "leaf"


def _plugin_dir() -> Path:
    return Path(__file__).resolve().parent


def _load_rules() -> dict:
    path = _plugin_dir() / "routing_rules.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _detect_stage(task_text: str, rules: dict) -> str:
    text = task_text.lower()
    stages = rules.get("stages", {})
    for stage, cfg in stages.items():
        for kw in cfg.get("keywords", []):
            if kw.lower() in text:
                return stage
    return rules.get("default_stage", "execution")


def _persona_for_stage(stage: str, rules: dict) -> str:
    return rules.get("stages", {}).get(stage, {}).get("persona", FEATURE_DEVELOPER)


def route_task(task_text: str, stage_override: Optional[str] = None) -> RouteDecision:
    rules = _load_rules()
    valid_stages = set(rules.get("stages", {}).keys())
    if stage_override and stage_override not in valid_stages:
        stage = rules.get("default_stage", "execution")
    else:
        stage = stage_override or _detect_stage(task_text, rules)
    persona = _persona_for_stage(stage, rules)

    if persona == PRINCIPAL_ENGINEER:
        reason = "Planning/refactor/evaluation work is routed to Principal Engineer."
    elif persona == PROJECT_MANAGER:
        reason = "Management/documentation/coordination work is routed to Project Manager."
    elif persona == FEATURE_DEVELOPER:
        reason = "Execution work is routed to Feature Developer."
    else:
        persona = FEATURE_DEVELOPER
        reason = "Unrecognized routing persona; defaulting to Feature Developer for execution."

    return RouteDecision(
        persona=persona,
        stage=stage,
        reason=reason,
        role=_role_for_persona(persona),
        toolsets=["terminal", "file"],
    )


def load_persona_markdown(persona: str) -> str:
    path = _plugin_dir() / "personas" / f"{persona}.md"
    return path.read_text(encoding="utf-8").strip()


def _build_payload(decision: RouteDecision, task_text: str, persona_md: str, guidance: str) -> dict:
    return {
        "goal": f"Complete this delegated task:\n{task_text}",
        "context": (
            "Apply this persona strictly while solving the task.\n\n"
            f"{persona_md}\n\n"
            f"{guidance}"
        ),
        "toolsets": decision.toolsets,
        "role": decision.role,
        "meta": {
            "source": "seer-agent",
            "persona": decision.persona,
            "stage": decision.stage,
        },
    }


def build_delegate_payload(task_text: str, stage_override: Optional[str] = None) -> tuple[RouteDecision, dict]:
    decision = route_task(task_text, stage_override=stage_override)
    persona_md = load_persona_markdown(decision.persona)
    guidance = (
        "If you are Principal Engineer: require precision for planning, ensure spec docs are captured in-repo, "
        "and for refactor/evaluation produce the 11 metric scores and exactly 5 most actionable moves.\n"
        "If you are Feature Developer: execute efficiently against spec, keep tests strong, and manually validate steps.\n"
        "If you are Project Manager: coordinate branch/docs/status hygiene, drive handoffs, and enforce merge discipline."
    )
    payload = _build_payload(decision, task_text, persona_md, guidance)
    return decision, payload


def build_delegate_payload_for_persona(persona: str, task_text: str, stage: str = "execution") -> tuple[RouteDecision, dict]:
    persona_name = (persona or "").strip()
    if persona_name not in {PRINCIPAL_ENGINEER, FEATURE_DEVELOPER, PROJECT_MANAGER}:
        persona_name = FEATURE_DEVELOPER
    persona_md = load_persona_markdown(persona_name)
    reason_map = {
        PRINCIPAL_ENGINEER: "Task explicitly delegated to Principal Engineer.",
        FEATURE_DEVELOPER: "Task explicitly delegated to Feature Developer.",
        PROJECT_MANAGER: "Task explicitly delegated to Project Manager.",
    }
    decision = RouteDecision(
        persona=persona_name,
        stage=(stage or "execution").strip() or "execution",
        reason=reason_map.get(persona_name, "Task explicitly delegated."),
        role=_role_for_persona(persona_name),
        toolsets=["terminal", "file"],
    )
    guidance = (
        "Respect persona boundaries. If the task requires another persona's responsibility, "
        "stop and report the handoff need."
    )
    payload = _build_payload(decision, task_text, persona_md, guidance)
    return decision, payload
