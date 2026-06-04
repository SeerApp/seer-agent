"""Register tool schemas and handlers for seer-agent."""

from __future__ import annotations

from ..core import operations
from ..types import JsonDict, SeerPluginContext


def business_brief_schema() -> JsonDict:
    return {
        "name": "seer_set_business_brief",
        "description": (
            "Set the required business brief before technical planning/execution. "
            "This must be captured first for vague product requests."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "objective": {"type": "string", "description": "Primary business objective."},
                "target_users": {"type": "string", "description": "Who the users/customers are."},
                "problem_statement": {"type": "string", "description": "Problem being solved."},
                "success_metrics": {"type": "string", "description": "How success will be measured."},
                "scope_in": {"type": "string", "description": "Explicitly in-scope capabilities."},
                "scope_out": {"type": "string", "description": "Explicitly out-of-scope capabilities."},
                "constraints": {"type": "string", "description": "Key constraints (time, risk, compliance, etc.)."},
                "current_stage": {"type": "string", "description": "Current stage (idea, MVP, growth, etc.)."},
            },
            "required": [
                "objective",
                "target_users",
                "problem_statement",
                "success_metrics",
                "scope_in",
                "scope_out",
                "constraints",
                "current_stage",
            ],
        },
    }


def business_refresh_schema() -> JsonDict:
    return {
        "name": "seer_refresh_business_brief",
        "description": "Infer and persist business brief from repository docs for this task/session.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Optional repository path. Defaults to current working directory."}
            },
            "required": [],
        },
    }


def register_tools(ctx: SeerPluginContext) -> None:
    ctx.register_tool(
        name="principal_engineer",
        toolset="delegation",
        schema={
            "name": "principal_engineer",
            "description": "Delegate planning/architecture/refactor/evaluation work to Principal Engineer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task to delegate."},
                    "stage": {"type": "string", "enum": ["planning", "refactor", "evaluation"], "description": "Optional explicit stage."},
                },
                "required": ["task"],
            },
        },
        handler=lambda args, **kw: operations.principal_engineer(task=args.get("task", ""), stage=args.get("stage", "planning"), ctx=ctx),
        description="Explicit Principal Engineer delegation.",
        emoji="🧠",
    )
    ctx.register_tool(
        name="feature_developer",
        toolset="delegation",
        schema={
            "name": "feature_developer",
            "description": "Delegate implementation work to Feature Developer (branch creation responsibility).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task to delegate."},
                    "stage": {"type": "string", "enum": ["execution"], "description": "Execution stage."},
                },
                "required": ["task"],
            },
        },
        handler=lambda args, **kw: operations.feature_developer(task=args.get("task", ""), stage=args.get("stage", "execution"), ctx=ctx),
        description="Explicit Feature Developer delegation.",
        emoji="🛠️",
    )
    ctx.register_tool(
        name="project_manager",
        toolset="delegation",
        schema={
            "name": "project_manager",
            "description": "Delegate project management tasks: docs hygiene, branch hygiene, status summaries, progress tracking, and merges into main/master.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task to delegate."},
                    "stage": {"type": "string", "description": "Optional management stage label."},
                },
                "required": ["task"],
            },
        },
        handler=lambda args, **kw: operations.project_manager(task=args.get("task", ""), stage=args.get("stage", "management"), ctx=ctx),
        description="Explicit Project Manager delegation.",
        emoji="📋",
    )
    ctx.register_tool(
        name="seer_set_business_brief",
        toolset="delegation",
        schema=business_brief_schema(),
        handler=lambda args, **kw: operations.set_business_brief(
            objective=args.get("objective", ""),
            target_users=args.get("target_users", ""),
            problem_statement=args.get("problem_statement", ""),
            success_metrics=args.get("success_metrics", ""),
            scope_in=args.get("scope_in", ""),
            scope_out=args.get("scope_out", ""),
            constraints=args.get("constraints", ""),
            current_stage=args.get("current_stage", ""),
            task_id=str(kw.get("task_id", "") or ""),
            session_id=str(kw.get("session_id", "") or ""),
        ),
        description="Capture business brief before technical work.",
        emoji="📌",
    )
    ctx.register_tool(
        name="seer_refresh_business_brief",
        toolset="delegation",
        schema=business_refresh_schema(),
        handler=lambda args, **kw: operations.refresh_business_brief_from_docs(
            repo_path=args.get("repo_path", ""),
            task_id=str(kw.get("task_id", "") or ""),
            session_id=str(kw.get("session_id", "") or ""),
        ),
        description="Infer and persist business brief from repository docs.",
        emoji="♻️",
    )

