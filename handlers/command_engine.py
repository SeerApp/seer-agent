"""Command engine for slash/SOUL helper logic."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Optional


def load_persona_markdown(
    *,
    plugin_dir: Path,
    persona_file: str,
    managed_start: str,
    managed_end: str,
    logger: logging.Logger,
) -> str:
    persona_path = plugin_dir / persona_file
    try:
        body = persona_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning("seer-agent: could not read %s: %s", persona_path, exc)
        body = "You are Seer Agent."
    return f"{managed_start}\n{body}\n{managed_end}"


def install_or_update_soul(
    *,
    soul_path: Path,
    managed_block: str,
    managed_start: str,
    managed_end: str,
    force: bool = False,
) -> tuple[str, Path]:
    soul_path.parent.mkdir(parents=True, exist_ok=True)
    if not soul_path.exists():
        soul_path.write_text(managed_block + "\n", encoding="utf-8")
        return "created", soul_path

    content = soul_path.read_text(encoding="utf-8")
    has_block = managed_start in content and managed_end in content
    if has_block and not force:
        return "already-installed", soul_path

    if has_block and force:
        start = content.index(managed_start)
        updated = content[:start].rstrip() + "\n\n" + managed_block + "\n"
        soul_path.write_text(updated, encoding="utf-8")
        return "updated", soul_path

    updated = content.rstrip() + "\n\n" + managed_block + "\n" if content.strip() else managed_block + "\n"
    soul_path.write_text(updated, encoding="utf-8")
    return "appended", soul_path


def render_status(
    *,
    soul_path: Path,
    managed_start: str,
    managed_end: str,
    feature_developer: str,
    principal_engineer: str,
    project_manager: str,
    has_repo_business_context: bool,
    business_source: str,
    has_brief: bool,
) -> str:
    if not soul_path.exists():
        return f"[seer-agent] No SOUL.md found at {soul_path}"
    content = soul_path.read_text(encoding="utf-8")
    installed = managed_start in content and managed_end in content
    return (
        f"[seer-agent] SOUL.md: {soul_path}\n"
        f"[seer-agent] Persona installed: {'yes' if installed else 'no'}\n"
        f"[seer-agent] Personas available: {feature_developer}, {principal_engineer}, {project_manager}\n"
        "[seer-agent] Delegation tools: principal_engineer, feature_developer, project_manager\n"
        "[seer-agent] Direct delegate_task: blocked by seer policy\n"
        "[seer-agent] Auto-route hinting: enabled for coding/Solana intents\n"
        f"[seer-agent] Repo business context detected: {'yes' if has_repo_business_context else 'no'} ({business_source})\n"
        f"[seer-agent] Business brief set (current session): {'yes' if has_brief else 'no'}"
    )


def handle_slash(
    *,
    raw_args: str,
    ctx,
    feature_developer: str,
    principal_engineer: str,
    project_manager: str,
    route_task: Callable[[str], object],
    delegate_to_persona: Callable[[str, str, str, object], str],
    refresh_business_brief_from_docs: Callable[[], str],
    install_or_update_soul: Callable[[bool], tuple[str, Path]],
    resolve_display_home: Callable[[], str],
    status_renderer: Callable[[], str],
) -> Optional[str]:
    argv = raw_args.strip().split()
    if not argv or argv[0] in {"help", "-h", "--help"}:
        return (
            "/seer-agent commands:\n"
            "  status\n"
            "  personas\n"
            "  route <task text>\n"
            "  delegate <task text>\n"
            "  business-refresh      # infer/store business brief from repo docs\n"
            "  install-soul        # add Seer persona block if missing\n"
            "  install-soul --force  # replace managed Seer block\n"
        )

    cmd = argv[0]
    if cmd == "status":
        return status_renderer()
    if cmd == "personas":
        return (
            "[seer-agent] Personas:\n"
            f"- {feature_developer}: feature execution + strong tests + manual validation\n"
            f"- {principal_engineer}: planning/architecture + refactor evaluation and scoring\n"
            f"- {project_manager}: documentation/status/progress and branch lifecycle stewardship"
        )
    if cmd == "route":
        task_text = raw_args[len("route"):].strip()
        if not task_text:
            return "Usage: /seer-agent route <task text>"
        decision = route_task(task_text)
        return (
            f"[seer-agent] Stage: {decision.stage}\n"
            f"[seer-agent] Persona: {decision.persona}\n"
            f"[seer-agent] Reason: {decision.reason}\n"
            f"[seer-agent] Toolsets: {', '.join(decision.toolsets)}"
        )
    if cmd == "delegate":
        if ctx is None:
            return "[seer-agent] Plugin context unavailable for delegation."
        task_text = raw_args[len("delegate"):].strip()
        if not task_text:
            return "Usage: /seer-agent delegate <task text>"
        decision = route_task(task_text)
        raw = delegate_to_persona(decision.persona, task_text, decision.stage, ctx)
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        summary = parsed.get("delegate_result", {}).get("summary") if isinstance(parsed, dict) else None
        return f"[seer-agent] Delegated to {decision.persona} (stage={decision.stage}).\n" + (
            summary if isinstance(summary, str) and summary.strip() else raw
        )
    if cmd == "business-refresh":
        return refresh_business_brief_from_docs()
    if cmd == "install-soul":
        force = "--force" in argv[1:]
        result, soul_path = install_or_update_soul(force)
        display_home = resolve_display_home()
        return (
            f"[seer-agent] {result} Seer persona block in {soul_path}\n"
            f"[seer-agent] Active Hermes home: {display_home}\n"
            "[seer-agent] Start a new session to guarantee prompt-cache-safe persona pickup."
        )
    return "Unknown subcommand. Run `/seer-agent help`."

