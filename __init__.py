"""seer-agent plugin: persona bootstrap utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
import json
import threading

from .router import build_delegate_payload, FEATURE_DEVELOPER, PRINCIPAL_ENGINEER, route_task

logger = logging.getLogger(__name__)


_MANAGED_START = "<!-- seer-agent persona:begin -->"
_MANAGED_END = "<!-- seer-agent persona:end -->"
_PERSONA_FILE = "seer_persona.md"
_AUTO_ROUTE_KEYWORDS = (
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

_GATE_LOCK = threading.Lock()
# key -> gate state for current task/session
_PRECISION_GATE: dict[str, dict[str, object]] = {}
_GATE_ALLOWED_TOOLS = {"clarify", "seer_delegate"}


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
        f"[seer-agent] Personas available: {FEATURE_DEVELOPER}, {PRINCIPAL_ENGINEER}\n"
        "[seer-agent] Routing tool: seer_delegate (recommended)\n"
        "[seer-agent] Direct delegate_task: blocked by seer policy\n"
        "[seer-agent] Auto-route hinting: enabled for coding/Solana intents"
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


def _seer_delegate(task: str, stage: str = "", ctx=None) -> str:
    """Model-callable routed delegation entrypoint."""
    if ctx is None:
        return json.dumps({"error": "Plugin context unavailable for delegation."})
    task_text = (task or "").strip()
    if not task_text:
        return json.dumps({"error": "task is required"})

    stage_override = stage.strip() if isinstance(stage, str) else ""
    decision, payload = build_delegate_payload(task_text, stage_override=stage_override or None)
    # Any seer_delegate call satisfies the precision gate for this turn scope.
    with _GATE_LOCK:
        for gate in _PRECISION_GATE.values():
            gate["satisfied"] = True
            gate["reason"] = "seer_delegate invoked"
    raw = ctx.dispatch_tool("delegate_task", payload)
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        pass
    return json.dumps(
        {
            "success": True,
            "routed_persona": decision.persona,
            "routed_stage": decision.stage,
            "reason": decision.reason,
            "delegate_result": parsed if isinstance(parsed, dict) else raw,
        }
    )


def _on_pre_tool_call(tool_name: str = "", args: Optional[dict] = None, **_) -> Optional[dict]:
    """Enforce Seer delegation policy by disallowing direct delegate_task calls."""
    task_id = _.get("task_id", "") if isinstance(_, dict) else ""
    session_id = _.get("session_id", "") if isinstance(_, dict) else ""
    gate_key = task_id or session_id or "default"

    # Precision gate: for vague coding asks, only clarify/seer_delegate may run
    # until precision is established.
    with _GATE_LOCK:
        gate = _PRECISION_GATE.get(gate_key)
    if gate and not gate.get("satisfied"):
        if tool_name not in _GATE_ALLOWED_TOOLS:
            return {
                "action": "block",
                "message": (
                    "seer-agent precision gate: request is too vague for execution. "
                    "First ask focused clarifying questions via the clarify tool or call "
                    "seer_delegate with stage='planning'."
                ),
            }
        if tool_name == "clarify":
            with _GATE_LOCK:
                if gate_key in _PRECISION_GATE:
                    _PRECISION_GATE[gate_key]["satisfied"] = True
                    _PRECISION_GATE[gate_key]["reason"] = "clarify invoked"
            return None

    if tool_name != "delegate_task":
        return None
    if isinstance(args, dict) and args.get("context") and "Apply this persona strictly while solving the task." in str(args.get("context")):
        # Already Seer-routed payload (from /seer-agent delegate or seer_delegate tool).
        return None
    return {
        "action": "block",
        "message": (
            "seer-agent policy: do not call delegate_task directly. "
            "Use the seer_delegate tool (or /seer-agent delegate) so routing can pick "
            "Principal Engineer for planning/refactor/evaluation and Feature Developer for execution."
        ),
    }


def _looks_like_coding_request(user_message: str) -> bool:
    text = (user_message or "").lower()
    return any(kw in text for kw in _AUTO_ROUTE_KEYWORDS)


def _looks_vague(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    words = text.split()
    has_scope_marker = any(
        marker in text
        for marker in (
            "acceptance criteria",
            "requirements",
            "spec",
            "milestone",
            "phase",
            "step",
            "tests",
            "instruction",
            "module",
            "file",
            "crate",
            "program id",
        )
    )
    return len(words) <= 20 and not has_scope_marker


def _on_pre_llm_call(user_message: str = "", **_) -> Optional[dict]:
    """Steer the model to use seer_delegate before coding work."""
    if not isinstance(user_message, str) or not user_message.strip():
        return None
    if not _looks_like_coding_request(user_message):
        return None
    task_id = _.get("task_id", "") if isinstance(_, dict) else ""
    session_id = _.get("session_id", "") if isinstance(_, dict) else ""
    gate_key = task_id or session_id or "default"
    vague = _looks_vague(user_message)
    with _GATE_LOCK:
        if vague:
            _PRECISION_GATE[gate_key] = {"satisfied": False, "reason": "vague prompt"}
        else:
            _PRECISION_GATE.pop(gate_key, None)
    return {
        "context": (
            "seer-agent policy reminder: this appears to be coding/planning/refactor work. "
            "Before implementation actions, call the `seer_delegate` tool so routing can choose "
            "Principal Engineer (planning/refactor/evaluation) or Feature Developer (execution). "
            + (
                "This prompt is currently vague: ask precise clarification questions first, "
                "or call seer_delegate with stage='planning'."
                if vague else
                "Proceed with routed delegation."
            )
        )
    }


def register(ctx) -> None:
    """Hermes plugin entrypoint."""
    logger.info("seer-agent plugin loaded")
    ctx.register_command(
        "seer-agent",
        handler=lambda raw_args: _handle_slash(raw_args, ctx=ctx),
        description="Install and inspect Seer persona in SOUL.md.",
    )
    ctx.register_tool(
        name="seer_delegate",
        toolset="delegation",
        schema={
            "name": "seer_delegate",
            "description": (
                "Route a task to Seer personas and delegate it. "
                "Planning/architecture/refactor/evaluation routes to Principal Engineer; "
                "execution routes to Feature Developer. Prefer this over delegate_task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task to delegate.",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["planning", "refactor", "evaluation", "execution"],
                        "description": "Optional explicit stage override.",
                    },
                },
                "required": ["task"],
            },
        },
        handler=lambda args, **kw: _seer_delegate(
            task=args.get("task", ""),
            stage=args.get("stage", ""),
            ctx=ctx,
        ),
        description="Seer-routed delegate wrapper with persona policy.",
        emoji="🧭",
    )
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
