"""seer-agent plugin: persona bootstrap utilities."""

from __future__ import annotations

import logging
import os
import subprocess
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
_BUSINESS_GATE: dict[str, dict[str, object]] = {}
_BUSINESS_BRIEF: dict[str, dict[str, str]] = {}
_GIT_GATE: dict[str, dict[str, object]] = {}
_GATE_ALLOWED_TOOLS = {
    "clarify",
    "seer_set_business_brief",
    "seer_refresh_business_brief",
    "seer_git_prepare",
    "seer_branch_finalize",
}
_CONVENTIONAL_TYPES = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
}
_BUSINESS_BRIEF_STORE_DIR = ".seer-agent"
_BUSINESS_BRIEF_STORE_FILE = "business_brief.json"
_BRANCH_POLICY_STORE_FILE = "branch_policy.json"
_BUSINESS_DOC_GLOBS = ("docs/*.md", "docs/**/*.md", "*.md")
_BUSINESS_DOC_MARKERS = (
    "objective",
    "target users",
    "problem statement",
    "success metrics",
    "scope in",
    "scope out",
    "constraints",
    "mvp",
)
_BUSINESS_BRIEF_FIELDS = (
    "objective",
    "target_users",
    "problem_statement",
    "success_metrics",
    "scope_in",
    "scope_out",
    "constraints",
    "current_stage",
)
_REASONABLE_GITIGNORE_LINES = (
    "# Seer baseline ignores",
    ".DS_Store",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    ".mypy_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    ".env",
    ".env.*",
    "*.log",
)
_LANGUAGE_GITIGNORE_PATTERNS = {
    "python": (
        ".ruff_cache/",
        ".coverage",
        "htmlcov/",
    ),
    "node_ts": (
        ".next/",
        ".turbo/",
        "*.tsbuildinfo",
        "coverage/",
    ),
    "rust": (
        "target/",
    ),
    "anchor_solana": (
        "test-ledger/",
        ".anchor/",
    ),
}


def _branch_policy_path(repo_root: Path) -> Path:
    return repo_root / _BUSINESS_BRIEF_STORE_DIR / _BRANCH_POLICY_STORE_FILE


def _load_branch_policy(repo_root: Path) -> dict:
    path = _branch_policy_path(repo_root)
    if not path.exists():
        return {"branches": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("branches"), dict):
            return raw
    except Exception:
        pass
    return {"branches": {}}


def _save_branch_policy(repo_root: Path, payload: dict) -> None:
    path = _branch_policy_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _set_branch_intent(repo_root: Path, branch: str, description: str) -> None:
    policy = _load_branch_policy(repo_root)
    branches = policy.setdefault("branches", {})
    branches[branch] = {"description": description.strip()}
    _save_branch_policy(repo_root, policy)


def _get_branch_intent(repo_root: Path, branch: str) -> str:
    policy = _load_branch_policy(repo_root)
    branches = policy.get("branches", {})
    entry = branches.get(branch, {})
    desc = entry.get("description", "") if isinstance(entry, dict) else ""
    return str(desc or "").strip()


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


def _run_cmd(command: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    return proc.returncode, output


def _resolve_repo_dir(repo_path: str = "") -> Path:
    if isinstance(repo_path, str) and repo_path.strip():
        return Path(repo_path).expanduser().resolve()
    return Path.cwd().resolve()


def _git_repo_root_from(repo_dir: Path) -> Optional[Path]:
    code, top = _run_cmd(["git", "rev-parse", "--show-toplevel"], repo_dir)
    if code != 0:
        return None
    return Path(top).resolve()


def _business_brief_store_path(repo_root: Path) -> Path:
    return repo_root / _BUSINESS_BRIEF_STORE_DIR / _BUSINESS_BRIEF_STORE_FILE


def _load_persisted_business_brief(repo_root: Path) -> Optional[dict]:
    path = _business_brief_store_path(repo_root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("brief") and isinstance(raw["brief"], dict):
            return raw["brief"]
    except Exception:
        return None
    return None


def _persist_business_brief(repo_root: Path, brief: dict) -> None:
    path = _business_brief_store_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"brief": brief}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _repo_has_business_docs(repo_root: Path) -> bool:
    markers = tuple(m.lower() for m in _BUSINESS_DOC_MARKERS)
    for pattern in _BUSINESS_DOC_GLOBS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            hits = sum(1 for marker in markers if marker in text)
            if hits >= 3:
                return True
    return False


def _normalize_field_value(value: str, fallback: str) -> str:
    clean = (value or "").strip()
    return clean if clean else fallback


def _extract_brief_from_docs(repo_root: Path) -> Optional[dict]:
    marker_aliases = {
        "objective": ("objective", "goal"),
        "target_users": ("target users", "target audience", "users", "customers"),
        "problem_statement": ("problem statement", "problem"),
        "success_metrics": ("success metrics", "success metric", "kpi", "metrics"),
        "scope_in": ("scope in", "in scope"),
        "scope_out": ("scope out", "out of scope"),
        "constraints": ("constraints", "limitations", "trade-offs"),
        "current_stage": ("current stage", "stage", "mvp"),
    }
    collected: dict[str, str] = {}
    files_seen = 0
    for pattern in _BUSINESS_DOC_GLOBS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            files_seen += 1
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for line in lines:
                low = line.strip().lower()
                if ":" not in low:
                    continue
                for field, aliases in marker_aliases.items():
                    if field in collected:
                        continue
                    for alias in aliases:
                        prefix = f"{alias}:"
                        if low.startswith(prefix):
                            collected[field] = line.split(":", 1)[1].strip()
                            break

    if not collected and files_seen == 0:
        return None
    if not collected and not _repo_has_business_docs(repo_root):
        return None

    return {
        "objective": _normalize_field_value(collected.get("objective", ""), "Defined in repository docs."),
        "target_users": _normalize_field_value(collected.get("target_users", ""), "Defined in repository docs."),
        "problem_statement": _normalize_field_value(collected.get("problem_statement", ""), "Defined in repository docs."),
        "success_metrics": _normalize_field_value(collected.get("success_metrics", ""), "Defined in repository docs."),
        "scope_in": _normalize_field_value(collected.get("scope_in", ""), "Defined in repository docs."),
        "scope_out": _normalize_field_value(collected.get("scope_out", ""), "Defined in repository docs."),
        "constraints": _normalize_field_value(collected.get("constraints", ""), "Defined in repository docs."),
        "current_stage": _normalize_field_value(collected.get("current_stage", ""), "Defined in repository docs."),
    }


def _resolve_repo_business_context(repo_path: str = "") -> tuple[bool, str]:
    repo_dir = _resolve_repo_dir(repo_path)
    repo_root = _git_repo_root_from(repo_dir)
    if repo_root is None:
        return False, "not-a-repo"
    if _load_persisted_business_brief(repo_root):
        return True, "persisted-brief"
    if _repo_has_business_docs(repo_root):
        return True, "docs-detected"
    return False, "not-found"


def _ensure_reasonable_gitignore(repo_root: Path) -> tuple[bool, str]:
    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    else:
        existing = []

    existing_set = {line.strip() for line in existing if line.strip()}
    missing = [line for line in _REASONABLE_GITIGNORE_LINES if line.strip() and line.strip() not in existing_set]
    if not missing:
        return False, "gitignore_already_reasonable"

    new_lines: list[str] = []
    if existing and existing[-1].strip():
        new_lines.append("")
    if "# Seer baseline ignores" not in existing_set:
        new_lines.append("# Seer baseline ignores")
    for line in missing:
        if line == "# Seer baseline ignores":
            continue
        new_lines.append(line)

    final = existing + new_lines
    gitignore_path.write_text("\n".join(final).rstrip() + "\n", encoding="utf-8")
    return True, f"gitignore_updated:{len(missing)}"


def _detect_repo_profiles(repo_root: Path) -> set[str]:
    profiles: set[str] = set()
    if any(repo_root.glob("**/*.py")) or (repo_root / "pyproject.toml").exists() or (repo_root / "requirements.txt").exists():
        profiles.add("python")
    if (repo_root / "package.json").exists() or any(repo_root.glob("**/*.ts")) or any(repo_root.glob("**/*.tsx")):
        profiles.add("node_ts")
    if (repo_root / "Cargo.toml").exists() or any(repo_root.glob("**/*.rs")):
        profiles.add("rust")
    if (repo_root / "Anchor.toml").exists() or (repo_root / "programs").exists():
        profiles.add("anchor_solana")
    return profiles


def _ensure_language_gitignore(repo_root: Path) -> tuple[bool, str]:
    profiles = _detect_repo_profiles(repo_root)
    if not profiles:
        return False, "gitignore_language_not_needed"

    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    else:
        existing = []
    existing_set = {line.strip() for line in existing if line.strip()}

    desired: list[str] = []
    for profile in sorted(profiles):
        desired.extend(_LANGUAGE_GITIGNORE_PATTERNS.get(profile, ()))
    missing = [line for line in desired if line.strip() and line.strip() not in existing_set]
    if not missing:
        return False, "gitignore_language_already_covered"

    new_lines: list[str] = []
    if existing and existing[-1].strip():
        new_lines.append("")
    new_lines.append("# Seer language-aware ignores")
    new_lines.extend(missing)

    final = existing + new_lines
    gitignore_path.write_text("\n".join(final).rstrip() + "\n", encoding="utf-8")
    return True, f"gitignore_language_updated:{len(missing)}"


def _refresh_business_brief_from_docs(repo_path: str = "", task_id: str = "", session_id: str = "") -> str:
    gate_key = task_id or session_id or "default"
    repo_dir = _resolve_repo_dir(repo_path)
    repo_root = _git_repo_root_from(repo_dir)
    if repo_root is None:
        return json.dumps({"success": False, "error": "Not inside a git repository."})
    inferred = _extract_brief_from_docs(repo_root)
    if not inferred:
        return json.dumps(
            {
                "success": False,
                "error": "Could not infer business brief from repository docs.",
                "hint": "Add business fields to docs or call seer_set_business_brief directly.",
            }
        )

    _persist_business_brief(repo_root, inferred)
    with _GATE_LOCK:
        _BUSINESS_BRIEF[gate_key] = inferred
        _BUSINESS_GATE[gate_key] = {"satisfied": True, "reason": "business brief refreshed from docs"}
    return json.dumps(
        {
            "success": True,
            "message": "Business brief refreshed from repository docs and persisted.",
            "repo_root": str(repo_root),
            "brief": inferred,
        }
    )


def _is_branch_relevant(branch_intent: str, user_message: str) -> bool:
    intent = (branch_intent or "").strip().lower()
    msg = (user_message or "").strip().lower()
    if not intent or not msg:
        return True
    intent_tokens = {tok for tok in intent.replace("/", " ").replace("-", " ").split() if len(tok) >= 4}
    if not intent_tokens:
        return True
    overlap = sum(1 for tok in intent_tokens if tok in msg)
    return overlap >= 1


def _extract_task_session_ids(kwargs: dict) -> tuple[str, str]:
    return str(kwargs.get("task_id", "") or ""), str(kwargs.get("session_id", "") or "")


def _build_conventional_header(
    commit_type: str,
    description: str,
    scope: str = "",
    breaking: bool = False,
) -> str:
    ctype = (commit_type or "").strip().lower()
    desc = (description or "").strip()
    cscope = (scope or "").strip()
    if ctype not in _CONVENTIONAL_TYPES:
        raise ValueError(f"Invalid commit type '{ctype}'.")
    if not desc:
        raise ValueError("description is required.")
    if cscope:
        return f"{ctype}({cscope}){'!' if breaking else ''}: {desc}"
    return f"{ctype}{'!' if breaking else ''}: {desc}"


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
    gate_key = "default"
    has_repo_business_context, business_source = _resolve_repo_business_context()
    with _GATE_LOCK:
        has_brief = gate_key in _BUSINESS_BRIEF
        git_ready = bool(_GIT_GATE.get(gate_key, {}).get("satisfied"))
    return (
        f"[seer-agent] SOUL.md: {soul_path}\n"
        f"[seer-agent] Persona installed: {'yes' if installed else 'no'}\n"
        f"[seer-agent] Personas available: {FEATURE_DEVELOPER}, {PRINCIPAL_ENGINEER}\n"
        "[seer-agent] Routing tool: seer_delegate (recommended)\n"
        "[seer-agent] Direct delegate_task: blocked by seer policy\n"
        "[seer-agent] Git workflow tools: seer_git_prepare + seer_git_checkpoint\n"
        "[seer-agent] Git hygiene: baseline + language-aware .gitignore enforced\n"
        "[seer-agent] Commit policy: conventional commits required for checkpoints\n"
        "[seer-agent] Auto-route hinting: enabled for coding/Solana intents\n"
        f"[seer-agent] Repo business context detected: {'yes' if has_repo_business_context else 'no'} ({business_source})\n"
        f"[seer-agent] Business brief set (current session): {'yes' if has_brief else 'no'}\n"
        f"[seer-agent] Git gate satisfied (current session): {'yes' if git_ready else 'no'}"
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
            "  git-prepare [branch]\n"
            "  branch-finalize [next-branch]\n"
            "  business-refresh      # infer/store business brief from repo docs\n"
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
    if cmd == "git-prepare":
        branch_name = argv[1] if len(argv) > 1 else ""
        return _seer_git_prepare(branch_name=branch_name)
    if cmd == "branch-finalize":
        next_branch = argv[1] if len(argv) > 1 else ""
        return _seer_branch_finalize(next_branch=next_branch)
    if cmd == "business-refresh":
        return _refresh_business_brief_from_docs()
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
    delegate_payload = parsed if isinstance(parsed, dict) else {"raw": raw}
    summary = ""
    if isinstance(parsed, dict):
        maybe_summary = parsed.get("summary")
        if isinstance(maybe_summary, str):
            summary = maybe_summary.strip()
    status = "completed"
    if isinstance(parsed, dict):
        for key in ("status", "state"):
            val = parsed.get(key)
            if isinstance(val, str) and val.strip():
                status = val.strip().lower()
                break
    return json.dumps(
        {
            "success": True,
            "delegation": {
                "to_persona": decision.persona,
                "stage": decision.stage,
                "status": status,
                "current_activity": (
                    f"{decision.persona} handled {decision.stage} scope for the delegated task."
                ),
                "task_preview": task_text[:180],
                "summary": summary or "Delegated run finished; inspect delegate_result for details.",
            },
            "routed_persona": decision.persona,
            "routed_stage": decision.stage,
            "reason": decision.reason,
            "delegate_result": delegate_payload,
        }
    )


def _seer_set_business_brief(
    objective: str = "",
    target_users: str = "",
    problem_statement: str = "",
    success_metrics: str = "",
    scope_in: str = "",
    scope_out: str = "",
    constraints: str = "",
    current_stage: str = "",
    task_id: str = "",
    session_id: str = "",
) -> str:
    """Capture the mandatory business brief before technical work."""
    gate_key = task_id or session_id or "default"
    repo_dir = _resolve_repo_dir("")
    repo_root = _git_repo_root_from(repo_dir)
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
        return json.dumps(
            {
                "success": False,
                "error": "Missing required business brief fields.",
                "missing_fields": missing,
            }
        )

    brief = {k: v.strip() for k, v in required.items()}
    with _GATE_LOCK:
        _BUSINESS_BRIEF[gate_key] = brief
        _BUSINESS_GATE[gate_key] = {"satisfied": True, "reason": "business brief captured"}
    if repo_root is not None:
        _persist_business_brief(repo_root, brief)
    return json.dumps({"success": True, "message": "Business brief captured.", "brief": brief})


def _seer_git_prepare(
    repo_path: str = "",
    branch_name: str = "",
    branch_description: str = "",
    task_id: str = "",
    session_id: str = "",
) -> str:
    gate_key = task_id or session_id or "default"
    repo_dir = _resolve_repo_dir(repo_path)
    if not repo_dir.exists() or not repo_dir.is_dir():
        return json.dumps({"success": False, "error": f"repo_path does not exist: {repo_dir}"})

    actions: list[str] = []
    if not (repo_dir / ".git").exists():
        code, out = _run_cmd(["git", "init"], repo_dir)
        if code != 0:
            return json.dumps({"success": False, "error": out or "git init failed"})
        actions.append("initialized_git_repo")

    code, top = _run_cmd(["git", "rev-parse", "--show-toplevel"], repo_dir)
    if code != 0:
        return json.dumps({"success": False, "error": top or "not a git repository"})
    repo_root = Path(top).resolve()

    updated_gitignore, gitignore_action = _ensure_reasonable_gitignore(repo_root)
    if updated_gitignore:
        actions.append(gitignore_action)
    updated_lang_gitignore, lang_gitignore_action = _ensure_language_gitignore(repo_root)
    if updated_lang_gitignore:
        actions.append(lang_gitignore_action)

    code, _ = _run_cmd(["git", "rev-parse", "--verify", "HEAD"], repo_root)
    if code != 0:
        _run_cmd(["git", "add", "-A"], repo_root)
        code, staged = _run_cmd(["git", "diff", "--cached", "--name-only"], repo_root)
        if code == 0 and staged.strip():
            code, out = _run_cmd(
                ["git", "commit", "-m", "chore(init): initialize repository for auditable development"],
                repo_root,
            )
            if code != 0:
                return json.dumps({"success": False, "error": out or "initial commit failed"})
            actions.append("created_initial_baseline_commit")

    target_branch = (branch_name or "").strip()
    if not target_branch:
        target_branch = f"seer/{gate_key.replace(' ', '-').lower()[:24]}"

    code, current_branch = _run_cmd(["git", "branch", "--show-current"], repo_root)
    if code != 0:
        current_branch = ""
    current_branch = (current_branch or "").strip()

    if target_branch and target_branch != current_branch:
        code, _ = _run_cmd(["git", "rev-parse", "--verify", target_branch], repo_root)
        if code == 0:
            code, out = _run_cmd(["git", "switch", target_branch], repo_root)
            if code != 0:
                return json.dumps({"success": False, "error": out or f"could not switch to {target_branch}"})
            actions.append(f"switched_branch:{target_branch}")
        else:
            code, out = _run_cmd(["git", "switch", "-c", target_branch], repo_root)
            if code != 0:
                return json.dumps({"success": False, "error": out or f"could not create {target_branch}"})
            actions.append(f"created_branch:{target_branch}")

    if (branch_description or "").strip():
        _set_branch_intent(repo_root, target_branch, branch_description)
        actions.append("recorded_branch_intent")
    else:
        existing_intent = _get_branch_intent(repo_root, target_branch)
        if not existing_intent:
            auto_intent = f"Task scope for {target_branch}"
            _set_branch_intent(repo_root, target_branch, auto_intent)
            actions.append("recorded_branch_intent")

    with _GATE_LOCK:
        _GIT_GATE[gate_key] = {
            "satisfied": True,
            "repo_root": str(repo_root),
            "branch": target_branch,
            "branch_intent": _get_branch_intent(repo_root, target_branch),
            "conventional_commits": True,
        }

    return json.dumps(
        {
            "success": True,
            "message": "Repository workflow prerequisites satisfied.",
            "repo_root": str(repo_root),
            "branch": target_branch,
            "actions": actions,
        }
    )


def _seer_git_checkpoint(
    commit_type: str = "",
    description: str = "",
    scope: str = "",
    body: str = "",
    tests: str = "",
    breaking: bool = False,
    task_id: str = "",
    session_id: str = "",
) -> str:
    gate_key = task_id or session_id or "default"
    with _GATE_LOCK:
        gate = _GIT_GATE.get(gate_key)
    if not gate or not gate.get("satisfied"):
        return json.dumps(
            {
                "success": False,
                "error": "Git gate not satisfied. Call seer_git_prepare before checkpoints.",
            }
        )

    repo_root = Path(str(gate.get("repo_root", ""))).resolve()
    if not repo_root.exists():
        return json.dumps({"success": False, "error": f"Repo path no longer exists: {repo_root}"})

    try:
        header = _build_conventional_header(commit_type, description, scope=scope, breaking=bool(breaking))
    except ValueError as exc:
        return json.dumps({"success": False, "error": str(exc), "allowed_types": sorted(_CONVENTIONAL_TYPES)})

    _run_cmd(["git", "add", "-A"], repo_root)
    code, staged = _run_cmd(["git", "diff", "--cached", "--name-only"], repo_root)
    if code != 0:
        return json.dumps({"success": False, "error": staged or "failed to inspect staged changes"})
    if not staged.strip():
        return json.dumps({"success": False, "error": "No staged changes to commit."})

    message_parts = [header]
    clean_body = (body or "").strip()
    clean_tests = (tests or "").strip()
    if clean_body:
        message_parts.append(clean_body)
    if clean_tests:
        message_parts.append(f"Tests: {clean_tests}")
    commit_message = "\n\n".join(message_parts)

    code, out = _run_cmd(["git", "commit", "-m", commit_message], repo_root)
    if code != 0:
        return json.dumps({"success": False, "error": out or "git commit failed"})

    code, commit_sha = _run_cmd(["git", "rev-parse", "--short", "HEAD"], repo_root)
    return json.dumps(
        {
            "success": True,
            "message": "Checkpoint committed with conventional commit format.",
            "commit": commit_sha.strip() if code == 0 else "",
            "header": header,
        }
    )


def _default_base_branch(repo_root: Path) -> str:
    for name in ("main", "master"):
        code, _ = _run_cmd(["git", "rev-parse", "--verify", name], repo_root)
        if code == 0:
            return name
    return "main"


def _seer_branch_finalize(
    base_branch: str = "",
    next_branch: str = "",
    next_branch_description: str = "",
    task_id: str = "",
    session_id: str = "",
) -> str:
    gate_key = task_id or session_id or "default"
    with _GATE_LOCK:
        gate = _GIT_GATE.get(gate_key)
    if not gate or not gate.get("satisfied"):
        return json.dumps({"success": False, "error": "Workflow prerequisites not satisfied."})

    repo_root = Path(str(gate.get("repo_root", ""))).resolve()
    if not repo_root.exists():
        return json.dumps({"success": False, "error": f"Repo path no longer exists: {repo_root}"})

    code, dirty = _run_cmd(["git", "status", "--porcelain"], repo_root)
    if code != 0:
        return json.dumps({"success": False, "error": dirty or "Failed to inspect git status."})
    if dirty.strip():
        return json.dumps({"success": False, "error": "Working tree is dirty. Commit/stash changes before finalizing."})

    code, current_branch = _run_cmd(["git", "branch", "--show-current"], repo_root)
    if code != 0 or not current_branch.strip():
        return json.dumps({"success": False, "error": "Could not determine current branch."})
    current_branch = current_branch.strip()

    target_base = (base_branch or "").strip() or _default_base_branch(repo_root)
    code, _ = _run_cmd(["git", "rev-parse", "--verify", target_base], repo_root)
    if code != 0:
        return json.dumps({"success": False, "error": f"Base branch does not exist: {target_base}"})
    if current_branch == target_base:
        return json.dumps({"success": False, "error": "Already on base branch; nothing to finalize."})

    code, out = _run_cmd(["git", "switch", target_base], repo_root)
    if code != 0:
        return json.dumps({"success": False, "error": out or f"Failed to switch to {target_base}"})
    code, out = _run_cmd(["git", "merge", "--no-ff", current_branch], repo_root)
    if code != 0:
        return json.dumps(
            {
                "success": False,
                "error": out or "Merge failed; resolve conflicts manually.",
                "base_branch": target_base,
                "branch": current_branch,
            }
        )

    actions = [f"merged:{current_branch}->{target_base}"]
    branch_to_use = target_base
    if (next_branch or "").strip():
        branch_to_use = next_branch.strip()
        code, _ = _run_cmd(["git", "rev-parse", "--verify", branch_to_use], repo_root)
        if code == 0:
            code, out = _run_cmd(["git", "switch", branch_to_use], repo_root)
            if code != 0:
                return json.dumps({"success": False, "error": out or f"Failed to switch to {branch_to_use}"})
            actions.append(f"switched_branch:{branch_to_use}")
        else:
            code, out = _run_cmd(["git", "switch", "-c", branch_to_use], repo_root)
            if code != 0:
                return json.dumps({"success": False, "error": out or f"Failed to create {branch_to_use}"})
            actions.append(f"created_branch:{branch_to_use}")
        if (next_branch_description or "").strip():
            _set_branch_intent(repo_root, branch_to_use, next_branch_description)
            actions.append("recorded_branch_intent")

    with _GATE_LOCK:
        _GIT_GATE[gate_key] = {
            "satisfied": True,
            "repo_root": str(repo_root),
            "branch": branch_to_use,
            "branch_intent": _get_branch_intent(repo_root, branch_to_use),
            "conventional_commits": True,
        }

    return json.dumps(
        {
            "success": True,
            "message": "Branch finalized and merged; ready for next scope.",
            "base_branch": target_base,
            "active_branch": branch_to_use,
            "actions": actions,
        }
    )


def _on_pre_tool_call(tool_name: str = "", args: Optional[dict] = None, **_) -> Optional[dict]:
    """Enforce Seer delegation policy by disallowing direct delegate_task calls."""
    task_id = _.get("task_id", "") if isinstance(_, dict) else ""
    session_id = _.get("session_id", "") if isinstance(_, dict) else ""
    gate_key = task_id or session_id or "default"

    # Business-intent gate: block technical progress until business brief exists.
    with _GATE_LOCK:
        b_gate = _BUSINESS_GATE.get(gate_key)
    if b_gate and not b_gate.get("satisfied"):
        if tool_name not in _GATE_ALLOWED_TOOLS:
            return {
                "action": "block",
                "message": (
                    "seer-agent business gate: business requirements are not yet defined. "
                    "Before any technical planning or implementation, call `clarify` to gather "
                    "business intent and then call `seer_set_business_brief` with the required fields."
                ),
            }
        return None

    # Git discipline gate: coding work must initialize git workflow first.
    with _GATE_LOCK:
        g_gate = _GIT_GATE.get(gate_key)
    if g_gate and not g_gate.get("satisfied"):
        if tool_name not in {"clarify", "seer_set_business_brief", "seer_git_prepare"}:
            return {
                "action": "block",
                "message": (
                    "seer-agent workflow gate: required repository prerequisites are not satisfied yet. "
                    "Run `seer_git_prepare` first, then continue normal execution flow."
                ),
            }
        return None
    if (
        tool_name not in _GATE_ALLOWED_TOOLS
        and tool_name not in {"seer_git_checkpoint", "seer_branch_finalize"}
        and g_gate
        and g_gate.get("satisfied")
    ):
        repo_root = Path(str(g_gate.get("repo_root", ""))).resolve()
        branch = str(g_gate.get("branch", "") or "")
        intent = str(g_gate.get("branch_intent", "") or "")
        if repo_root.exists() and branch and not intent:
            intent = _get_branch_intent(repo_root, branch)
            if intent:
                with _GATE_LOCK:
                    if gate_key in _GIT_GATE:
                        _GIT_GATE[gate_key]["branch_intent"] = intent
        user_message = str(_.get("user_message", "") if isinstance(_, dict) else "")
        if intent and user_message and not _is_branch_relevant(intent, user_message):
            return {
                "action": "block",
                "message": (
                    "seer-agent branch scope gate: requested work appears out-of-scope for the active branch. "
                    "Use `seer_branch_finalize` to merge completed work and move to an appropriate branch, "
                    "or rerun `seer_git_prepare` with a branch matching this task."
                ),
            }

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
                    "First ask focused clarifying questions via the clarify tool."
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


def _looks_business_vague(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    business_markers = (
        "for who",
        "target user",
        "customer",
        "problem",
        "goal",
        "success metric",
        "mvp",
        "scope",
        "revenue",
        "market",
    )
    has_business_marker = any(m in text for m in business_markers)
    return _looks_like_coding_request(text) and not has_business_marker


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
    business_vague = _looks_business_vague(user_message)
    has_repo_business_context, business_source = _resolve_repo_business_context()
    with _GATE_LOCK:
        if business_vague:
            if has_repo_business_context:
                _BUSINESS_GATE[gate_key] = {
                    "satisfied": True,
                    "reason": f"business context already present ({business_source})",
                }
            else:
                _BUSINESS_GATE[gate_key] = {"satisfied": False, "reason": "missing business brief"}
        elif gate_key in _BUSINESS_GATE and gate_key not in _BUSINESS_BRIEF:
            if has_repo_business_context:
                _BUSINESS_GATE[gate_key] = {
                    "satisfied": True,
                    "reason": f"business context already present ({business_source})",
                }
            else:
                _BUSINESS_GATE[gate_key] = {"satisfied": False, "reason": "business brief required"}
        else:
            _BUSINESS_GATE.pop(gate_key, None)
        if vague:
            _PRECISION_GATE[gate_key] = {"satisfied": False, "reason": "vague prompt"}
        else:
            _PRECISION_GATE.pop(gate_key, None)
        if gate_key not in _GIT_GATE:
            _GIT_GATE[gate_key] = {"satisfied": False, "reason": "git workflow not prepared"}
    return {
        "context": (
            (
                "seer-agent strict business-first policy: this request is missing business intent. "
                "Your next action MUST be a single `clarify` tool call focused on business goals "
                "(objective, target users, problem statement, success metrics, in-scope/out-of-scope, constraints, stage). "
                "After clarification, call `seer_set_business_brief` with all required fields. "
                "Do not perform technical planning or implementation before the brief is captured."
                if business_vague and not has_repo_business_context
                else
                (
                    "seer-agent strict policy: this coding request is vague. "
                    "Your next action MUST be a single `clarify` tool call immediately. "
                    "Do not produce free-form analysis, plans, or long reasoning before clarifying. "
                    "Ask concise, high-leverage questions that pin down scope, constraints, success criteria, "
                    "and the first deliverable. After clarify resolves ambiguity, call `seer_delegate` "
                    "with stage='planning'."
                    if vague
                    else
                    "seer-agent workflow policy: this appears to be coding/planning/refactor work. "
                    "Before implementation actions, satisfy repository prerequisites by calling `seer_git_prepare`, "
                    "then call `seer_delegate` so routing can choose "
                    "Principal Engineer (planning/refactor/evaluation) or Feature Developer (execution). "
                    "Keep work aligned to active branch scope; if scope is complete or changed, finalize/merge via "
                    "`seer_branch_finalize` and continue on an appropriate branch. "
                    "Continue using checkpoints throughout execution. "
                    "Do not discuss internal workflow mechanics in user-facing responses unless explicitly asked."
                )
            )
        )
    }


def _business_brief_schema() -> dict:
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
    

def _business_brief_handler(args: dict, **kwargs) -> str:
    task_id, session_id = _extract_task_session_ids(kwargs)
    return _seer_set_business_brief(
        objective=args.get("objective", ""),
        target_users=args.get("target_users", ""),
        problem_statement=args.get("problem_statement", ""),
        success_metrics=args.get("success_metrics", ""),
        scope_in=args.get("scope_in", ""),
        scope_out=args.get("scope_out", ""),
        constraints=args.get("constraints", ""),
        current_stage=args.get("current_stage", ""),
        task_id=task_id,
        session_id=session_id,
    )


def _git_prepare_schema() -> dict:
    return {
        "name": "seer_git_prepare",
        "description": (
            "Prepare disciplined git workflow for the current task. "
            "Initializes git if missing, ensures a task branch, enforces conventional commits, "
            "and ensures a reasonable baseline .gitignore."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Optional repository path. Defaults to current working directory.",
                },
                "branch_name": {
                    "type": "string",
                    "description": "Optional branch to switch/create for task work.",
                },
                "branch_description": {
                    "type": "string",
                    "description": "Short branch intent. Work on the branch must stay aligned to this scope.",
                },
            },
            "required": [],
        },
    }


def _git_prepare_handler(args: dict, **kwargs) -> str:
    task_id, session_id = _extract_task_session_ids(kwargs)
    return _seer_git_prepare(
        repo_path=args.get("repo_path", ""),
        branch_name=args.get("branch_name", ""),
        branch_description=args.get("branch_description", ""),
        task_id=task_id,
        session_id=session_id,
    )


def _git_checkpoint_schema() -> dict:
    return {
        "name": "seer_git_checkpoint",
        "description": (
            "Create an auditable checkpoint commit using conventional commits. "
            "Use after each meaningful implementation step."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commit_type": {
                    "type": "string",
                    "description": "Conventional commit type (feat, fix, docs, refactor, test, chore, etc.).",
                },
                "scope": {"type": "string", "description": "Optional conventional commit scope."},
                "description": {"type": "string", "description": "Short imperative summary."},
                "body": {"type": "string", "description": "Optional explanatory commit body."},
                "tests": {"type": "string", "description": "Optional tests/validation evidence."},
                "breaking": {"type": "boolean", "description": "Set true for breaking changes."},
            },
            "required": ["commit_type", "description"],
        },
    }


def _git_checkpoint_handler(args: dict, **kwargs) -> str:
    task_id, session_id = _extract_task_session_ids(kwargs)
    return _seer_git_checkpoint(
        commit_type=args.get("commit_type", ""),
        description=args.get("description", ""),
        scope=args.get("scope", ""),
        body=args.get("body", ""),
        tests=args.get("tests", ""),
        breaking=bool(args.get("breaking", False)),
        task_id=task_id,
        session_id=session_id,
    )


def _branch_finalize_schema() -> dict:
    return {
        "name": "seer_branch_finalize",
        "description": (
            "Finalize current branch by merging completed task scope to base branch, "
            "then optionally switch/create the next branch for continued work."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "base_branch": {"type": "string", "description": "Optional merge target branch (defaults to main/master)."},
                "next_branch": {"type": "string", "description": "Optional next branch to continue work."},
                "next_branch_description": {
                    "type": "string",
                    "description": "Optional intent for next branch scope.",
                },
            },
            "required": [],
        },
    }


def _branch_finalize_handler(args: dict, **kwargs) -> str:
    task_id, session_id = _extract_task_session_ids(kwargs)
    return _seer_branch_finalize(
        base_branch=args.get("base_branch", ""),
        next_branch=args.get("next_branch", ""),
        next_branch_description=args.get("next_branch_description", ""),
        task_id=task_id,
        session_id=session_id,
    )


def _business_refresh_schema() -> dict:
    return {
        "name": "seer_refresh_business_brief",
        "description": "Infer and persist business brief from repository docs for this task/session.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Optional repository path. Defaults to current working directory.",
                }
            },
            "required": [],
        },
    }


def _business_refresh_handler(args: dict, **kwargs) -> str:
    task_id, session_id = _extract_task_session_ids(kwargs)
    return _refresh_business_brief_from_docs(
        repo_path=args.get("repo_path", ""),
        task_id=task_id,
        session_id=session_id,
    )


def _register_tools(ctx) -> None:
    ctx.register_tool(
        name="seer_git_prepare",
        toolset="delegation",
        schema=_git_prepare_schema(),
        handler=_git_prepare_handler,
        description="Initialize/enforce disciplined git workflow for current task.",
        emoji="🌱",
    )
    ctx.register_tool(
        name="seer_git_checkpoint",
        toolset="delegation",
        schema=_git_checkpoint_schema(),
        handler=_git_checkpoint_handler,
        description="Create conventional-commit checkpoints for auditable progress.",
        emoji="✅",
    )
    ctx.register_tool(
        name="seer_branch_finalize",
        toolset="delegation",
        schema=_branch_finalize_schema(),
        handler=_branch_finalize_handler,
        description="Merge completed branch and continue on next appropriate branch.",
        emoji="🔀",
    )
    ctx.register_tool(
        name="seer_set_business_brief",
        toolset="delegation",
        schema=_business_brief_schema(),
        handler=_business_brief_handler,
        description="Capture business brief before technical work.",
        emoji="📌",
    )
    ctx.register_tool(
        name="seer_refresh_business_brief",
        toolset="delegation",
        schema=_business_refresh_schema(),
        handler=_business_refresh_handler,
        description="Infer and persist business brief from repository docs.",
        emoji="♻️",
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
                

def register(ctx) -> None:
    """Hermes plugin entrypoint."""
    logger.info("seer-agent plugin loaded")
    ctx.register_command(
        "seer-agent",
        handler=lambda raw_args: _handle_slash(raw_args, ctx=ctx),
        description="Install and inspect Seer persona in SOUL.md.",
    )
    _register_tools(ctx)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
