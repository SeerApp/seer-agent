"""Routing logic for Seer subagent personas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PRINCIPAL_ENGINEER = "principal_engineer"
FEATURE_DEVELOPER = "feature_developer"

PRINCIPAL_STAGES = {"planning", "refactor", "evaluation"}


@dataclass
class RouteDecision:
    persona: str
    stage: str
    reason: str
    role: str
    toolsets: list[str]


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
    stage = stage_override or _detect_stage(task_text, rules)
    persona = _persona_for_stage(stage, rules)

    if persona == PRINCIPAL_ENGINEER:
        reason = "Planning/refactor/evaluation work is routed to Principal Engineer."
        return RouteDecision(
            persona=persona,
            stage=stage,
            reason=reason,
            role="leaf",
            toolsets=["terminal", "file"],
        )

    reason = "Execution work is routed to Feature Developer."
    return RouteDecision(
        persona=FEATURE_DEVELOPER,
        stage=stage,
        reason=reason,
        role="leaf",
        toolsets=["terminal", "file"],
    )


def load_persona_markdown(persona: str) -> str:
    path = _plugin_dir() / "personas" / f"{persona}.md"
    return path.read_text(encoding="utf-8").strip()


def build_delegate_payload(task_text: str, stage_override: Optional[str] = None) -> tuple[RouteDecision, dict]:
    decision = route_task(task_text, stage_override=stage_override)
    persona_md = load_persona_markdown(decision.persona)

    goal = f"Complete this delegated task:\n{task_text}"
    context = (
        "Apply this persona strictly while solving the task.\n\n"
        f"{persona_md}\n\n"
        "If you are Principal Engineer: require precision for planning, ensure spec docs are captured in-repo, "
        "and for refactor/evaluation produce the 11 metric scores and exactly 5 most actionable moves.\n"
        "If you are Feature Developer: execute efficiently against spec, keep tests strong, and manually validate steps."
    )
    payload = {
        "goal": goal,
        "context": context,
        "toolsets": decision.toolsets,
        "role": decision.role,
    }
    return decision, payload
