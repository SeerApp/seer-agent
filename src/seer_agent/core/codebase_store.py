"""Catalog and on-disk layout for locally cloned Solana codebases."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ..home import resolve_hermes_home
from ..paths import package_dir

_CATALOG_FILE = "codebases.json"
_STORE_SEGMENTS = ("seer-agent", "codebases")


def resolve_codebases_root(home: Path | None = None) -> Path:
    """Root directory for cloned repos (profile-local under ``HERMES_HOME``)."""
    override = os.environ.get("SEER_CODEBASES_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    base = home if home is not None else resolve_hermes_home()
    return base.joinpath(*_STORE_SEGMENTS).resolve()


def catalog_path() -> Path:
    """Bundled name → git URL map shipped with the plugin."""
    return package_dir() / _CATALOG_FILE


def load_catalog() -> dict[str, str]:
    with catalog_path().open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def catalog_names() -> list[str]:
    return sorted(load_catalog())


def local_path(name: str, home: Path | None = None) -> Path:
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


def is_available(name: str, home: Path | None = None) -> bool:
    """True when ``name`` is in the catalog and a git checkout exists on disk."""
    if name not in load_catalog():
        return False
    return is_git_repo(local_path(name, home=home))
