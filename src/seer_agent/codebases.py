"""Codebase catalog and on-disk clone layout for seer-agent."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TypedDict

from .home import resolve_hermes_home
from .paths import package_dir

_CATALOG_FILE = "codebases.json"
_STORE_SEGMENTS = ("seer-agent", "codebases")


class CodebaseEntry(TypedDict):
    git: str
    description: str
    docs: str


class CodebaseSummary(TypedDict):
    name: str
    description: str
    docs: str


def resolve_codebases_root(home: Path | None = None) -> Path:
    """Root directory for cloned repos (profile-local under ``HERMES_HOME``)."""
    override = os.environ.get("SEER_CODEBASES_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    base = home if home is not None else resolve_hermes_home()
    return base.joinpath(*_STORE_SEGMENTS).resolve()


def codebase_store_clone_guidance(home: Path | None = None) -> str:
    """Agent-facing text: canonical clone location for catalog codebases."""
    store_root = resolve_codebases_root(home=home)
    example = store_root / "agave"
    return (
        f"Catalog codebases MUST be git cloned only under {store_root}/<name>/ "
        f"(example: {example}). Do not clone them to ~/projects, the session cwd, "
        f"or any other path—availability is checked only in the store."
    )


def catalog_path() -> Path:
    """Bundled name → git URL map shipped with the plugin."""
    return package_dir() / _CATALOG_FILE


def _parse_catalog_entry(value: object) -> CodebaseEntry | None:
    if isinstance(value, dict):
        git = value.get("git")
        if not isinstance(git, str) or not git.strip():
            return None
        description = value.get("description")
        docs = value.get("docs")
        return {
            "git": git.strip(),
            "description": description.strip() if isinstance(description, str) else "",
            "docs": docs.strip() if isinstance(docs, str) else "",
        }
    if isinstance(value, str) and value.strip():
        return {"git": value.strip(), "description": "", "docs": ""}
    return None


def load_catalog() -> dict[str, CodebaseEntry]:
    with catalog_path().open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    catalog: dict[str, CodebaseEntry] = {}
    for key, value in raw.items():
        entry = _parse_catalog_entry(value)
        if entry is not None:
            catalog[str(key)] = entry
    return catalog


def catalog_names() -> list[str]:
    return sorted(load_catalog())


def codebase_git_url(name: str) -> str | None:
    entry = load_catalog().get(name)
    if entry is None:
        return None
    return entry["git"]


def catalog_summaries() -> list[CodebaseSummary]:
    summaries: list[CodebaseSummary] = []
    for name in catalog_names():
        entry = load_catalog()[name]
        summaries.append(
            {
                "name": name,
                "description": entry["description"],
                "docs": entry["docs"],
            }
        )
    return summaries


def codebase_local_path(name: str, home: Path | None = None) -> Path:
    """Expected clone directory for a catalog codebase."""
    return resolve_codebases_root(home=home) / name


def is_git_repo(path: Path) -> bool:
    if not path.is_dir():
        return False
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip().lower() == "true"


def remote_origin_url(path: Path) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    return url or None


def is_codebase_available(name: str, home: Path | None = None) -> bool:
    """True when ``name`` is in the catalog and a git checkout exists on disk."""
    if name not in load_catalog():
        return False
    return is_git_repo(codebase_local_path(name, home=home))
