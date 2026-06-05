"""Runtime/path/git/doc helpers for seer-agent."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

def soul_path(home: Path) -> Path:
    return home / "SOUL.md"


def run_cmd(command: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    return proc.returncode, output


def resolve_repo_dir(repo_path: str = "") -> Path:
    if isinstance(repo_path, str) and repo_path.strip():
        return Path(repo_path).expanduser().resolve()
    return Path.cwd().resolve()


def git_repo_root_from(repo_dir: Path) -> Optional[Path]:
    code, top = run_cmd(["git", "rev-parse", "--show-toplevel"], repo_dir)
    if code != 0:
        return None
    return Path(top).resolve()


def repo_has_business_docs(repo_root: Path, doc_globs: tuple[str, ...], doc_markers: tuple[str, ...]) -> bool:
    markers = tuple(m.lower() for m in doc_markers)
    for pattern in doc_globs:
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


def extract_brief_from_docs(repo_root: Path, doc_globs: tuple[str, ...]) -> Optional[dict]:
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
    for pattern in doc_globs:
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
    if not collected:
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

