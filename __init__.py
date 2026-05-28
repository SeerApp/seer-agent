"""seer-agent plugin: persona bootstrap utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
import json

from .router import build_delegate_payload, FEATURE_DEVELOPER, PRINCIPAL_ENGINEER, route_task

logger = logging.getLogger(__name__)


_MANAGED_START = "<!-- seer-agent persona:begin -->"
_MANAGED_END = "<!-- seer-agent persona:end -->"
_PERSONA_FILE = "seer_persona.md"


def _resolve_hermes_home() -> Path:
    """Resolve active HERMES_HOME in a profile-safe way."""
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home()
    except Exception:
        env_home = os.environ.get("HERMES_HOME")
        if env_home:
            return Path(env_home).expanduser()
        return Path.home() / ".hermes"


def _resolve_display_home(home: Path) -> str:
    try:
        from hermes_constants import display_hermes_home

        return str(display_hermes_home())
    except Exception:
        return str(home)


def _soul_path() -> Path:
    return _resolve_hermes_home() / "SOUL.md"


def _plugin_dir() -> Path:
    return Path(__file__).resolve().parent


def _load_persona_markdown() -> str:
    persona_path = _plugin_dir() / _PERSONA_FILE
    try:
        body = persona_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning("seer-agent: could not read %s: %s", persona_path, exc)
        body = "You are Seer Agent."
    return f"{_MANAGED_START}\n{body}\n{_MANAGED_END}"


def _install_or_update_soul(force: bool = False) -> tuple[str, Path]:
    """Install Seer persona into SOUL.md.

    force=False: append managed block if absent.
    force=True: replace existing managed block, or append if absent.
    """
    soul_path = _soul_path()
    soul_path.parent.mkdir(parents=True, exist_ok=True)
    managed_block = _load_persona_markdown()

    if not soul_path.exists():
        soul_path.write_text(managed_block + "\n", encoding="utf-8")
        return "created", soul_path

    content = soul_path.read_text(encoding="utf-8")
    has_block = _MANAGED_START in content and _MANAGED_END in content

    if has_block and not force:
        return "already-installed", soul_path

    if has_block and force:
        start = content.index(_MANAGED_START)
        end = content.index(_MANAGED_END) + len(_MANAGED_END)
        updated = content[:start].rstrip() + "\n\n" + managed_block + "\n"
        soul_path.write_text(updated, encoding="utf-8")
        return "updated", soul_path

    if content.strip():
        updated = content.rstrip() + "\n\n" + managed_block + "\n"
    else:
        updated = managed_block + "\n"
    soul_path.write_text(updated, encoding="utf-8")
    return "appended", soul_path


def _status() -> str:
    soul_path = _soul_path()
    if not soul_path.exists():
        return f"[seer-agent] No SOUL.md found at {soul_path}"
    content = soul_path.read_text(encoding="utf-8")
    installed = _MANAGED_START in content and _MANAGED_END in content
    return (
        f"[seer-agent] SOUL.md: {soul_path}\n"
        f"[seer-agent] Persona installed: {'yes' if installed else 'no'}\n"
        f"[seer-agent] Personas available: {FEATURE_DEVELOPER}, {PRINCIPAL_ENGINEER}"
    )


def _handle_slash(raw_args: str, ctx=None) -> Optional[str]:
    argv = raw_args.strip().split()
    if not argv or argv[0] in {"help", "-h", "--help"}:
        return (
            "/seer-agent commands:\n"
            "  status\n"
            "  personas\n"
            "  route <task text>\n"
            "  delegate <task text>\n"
            "  install-soul        # add Seer persona block if missing\n"
            "  install-soul --force  # replace managed Seer block\n"
        )

    cmd = argv[0]
    if cmd == "status":
        return _status()
    if cmd == "personas":
        return (
            "[seer-agent] Personas:\n"
            f"- {FEATURE_DEVELOPER}: feature execution + strong tests + manual validation\n"
            f"- {PRINCIPAL_ENGINEER}: planning/architecture + refactor evaluation and scoring"
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
        decision, payload = build_delegate_payload(task_text)
        raw = ctx.dispatch_tool("delegate_task", payload)
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        summary = parsed.get("summary") if isinstance(parsed, dict) else None
        return (
            f"[seer-agent] Delegated to {decision.persona} (stage={decision.stage}).\n"
            + (summary if isinstance(summary, str) and summary.strip() else raw)
        )
    if cmd == "install-soul":
        force = "--force" in argv[1:]
        result, soul_path = _install_or_update_soul(force=force)
        display_home = _resolve_display_home(_resolve_hermes_home())
        return (
            f"[seer-agent] {result} Seer persona block in {soul_path}\n"
            f"[seer-agent] Active Hermes home: {display_home}\n"
            "[seer-agent] Start a new session to guarantee prompt-cache-safe persona pickup."
        )

    return "Unknown subcommand. Run `/seer-agent help`."


def register(ctx) -> None:
    """Hermes plugin entrypoint."""
    logger.info("seer-agent plugin loaded")
    ctx.register_command(
        "seer-agent",
        handler=lambda raw_args: _handle_slash(raw_args, ctx=ctx),
        description="Install and inspect Seer persona in SOUL.md.",
    )
