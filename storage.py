"""Persistence helpers for seer-agent policy/state files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def branch_policy_path(repo_root: Path, store_dir: str, branch_policy_file: str) -> Path:
    return repo_root / store_dir / branch_policy_file


def decision_policy_path(repo_root: Path, store_dir: str, decision_policy_file: str) -> Path:
    return repo_root / store_dir / decision_policy_file


def task_policy_path(repo_root: Path, store_dir: str, task_policy_file: str) -> Path:
    return repo_root / store_dir / task_policy_file


def business_brief_store_path(repo_root: Path, store_dir: str, business_brief_file: str) -> Path:
    return repo_root / store_dir / business_brief_file


def load_task_policy(path: Path) -> dict:
    if not path.exists():
        return {"branches": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("branches"), dict):
            return raw
    except Exception:
        pass
    return {"branches": {}}


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def load_decision_policy(path: Path) -> dict:
    if not path.exists():
        return {"decisions": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("decisions"), dict):
            return raw
    except Exception:
        pass
    return {"decisions": {}}


def load_branch_policy(path: Path) -> dict:
    if not path.exists():
        return {"branches": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("branches"), dict):
            return raw
    except Exception:
        pass
    return {"branches": {}}


def load_persisted_business_brief(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("brief") and isinstance(raw["brief"], dict):
            return raw["brief"]
    except Exception:
        return None
    return None

