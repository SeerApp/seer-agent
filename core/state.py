"""Shared constants and runtime state for seer-agent."""

from __future__ import annotations

import threading

MANAGED_START = "<!-- seer-agent persona:begin -->"
MANAGED_END = "<!-- seer-agent persona:end -->"
PERSONA_FILE = "seer_persona.md"

AUTO_ROUTE_KEYWORDS = (
    "solana",
    "anchor",
    "program",
    "instruction",
    "cpi",
    "idl",
    "refactor",
    "architecture",
    "design",
    "spec",
    "implement",
    "feature",
    "test",
    "codebase",
)

BUSINESS_BRIEF_STORE_DIR = ".seer-agent"
BUSINESS_BRIEF_STORE_FILE = "business_brief.json"
BRANCH_POLICY_STORE_FILE = "branch_policy.json"
DECISION_POLICY_STORE_FILE = "decision_policy.json"
TASK_POLICY_STORE_FILE = "task_policy.json"
BUSINESS_DOC_GLOBS = ("docs/*.md", "docs/**/*.md", "*.md")
BUSINESS_DOC_MARKERS = (
    "objective",
    "target users",
    "problem statement",
    "success metrics",
    "scope in",
    "scope out",
    "constraints",
    "mvp",
)
BUSINESS_BRIEF_FIELDS = (
    "objective",
    "target_users",
    "problem_statement",
    "success_metrics",
    "scope_in",
    "scope_out",
    "constraints",
    "current_stage",
)

GATE_ALLOWED_TOOLS = {
    "clarify",
    "seer_set_business_brief",
    "seer_refresh_business_brief",
    "principal_engineer",
    "feature_developer",
    "project_manager",
}

GATE_LOCK = threading.Lock()
PRECISION_GATE: dict[str, dict[str, object]] = {}
BUSINESS_GATE: dict[str, dict[str, object]] = {}
BUSINESS_BRIEF: dict[str, dict[str, str]] = {}
GIT_GATE: dict[str, dict[str, object]] = {}
AMBIGUITY_GATE: dict[str, dict[str, object]] = {}
ACTIVE_PERSONA: dict[str, str] = {}

