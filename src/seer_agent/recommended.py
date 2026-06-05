"""Recommended CLI tool catalog for seer-agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from .paths import package_dir

_RECOMMENDED_FILE = "recommended.json"


class RecommendedToolEntry(TypedDict):
    description: str
    check: str
    download: str
    docs: str
    verify: str


class RecommendedToolSummary(TypedDict):
    name: str
    description: str
    check: str
    download: str
    docs: str
    verify: str


def recommended_path() -> Path:
    return package_dir() / _RECOMMENDED_FILE


def _parse_recommended_tool_entry(value: object) -> RecommendedToolEntry | None:
    if not isinstance(value, dict):
        return None
    description = value.get("description")
    check = value.get("check")
    download = value.get("download")
    if not isinstance(description, str) or not description.strip():
        return None
    if not isinstance(check, str) or not check.strip():
        return None
    if not isinstance(download, str) or not download.strip():
        return None
    docs = value.get("docs")
    verify = value.get("verify")
    return {
        "description": description.strip(),
        "check": check.strip(),
        "download": download.strip(),
        "docs": docs.strip() if isinstance(docs, str) else "",
        "verify": verify.strip() if isinstance(verify, str) else "",
    }


def load_recommended_tools() -> dict[str, RecommendedToolEntry]:
    with recommended_path().open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    tools: dict[str, RecommendedToolEntry] = {}
    for key, value in raw.items():
        entry = _parse_recommended_tool_entry(value)
        if entry is not None:
            tools[str(key)] = entry
    return tools


def recommended_tool_names() -> list[str]:
    return sorted(load_recommended_tools())


def recommended_tool_summaries() -> list[RecommendedToolSummary]:
    summaries: list[RecommendedToolSummary] = []
    for name in recommended_tool_names():
        entry = load_recommended_tools()[name]
        summaries.append(
            {
                "name": name,
                "description": entry["description"],
                "check": entry["check"],
                "download": entry["download"],
                "docs": entry["docs"],
                "verify": entry["verify"],
            }
        )
    return summaries
