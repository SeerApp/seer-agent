import json
from pathlib import Path

from ...paths import package_dir
from ...types import JsonDict


NAME = "is_codebase_available"


def schema() -> JsonDict:
    return {
        "name": "is_codebase_available",
        "description": "Check if specified Solana codebase is on the machine.",
        "parameters": {
            "type": "object",
            "properties": {
                "codebase": {
                    "type": "string",
                    "enum": _codebase_names(),
                    "description": "Known Solana codebase to check for local availability.",
                },
            },
            "required": ["codebase"],
        },
    }


def handler(codebase: str) -> str:
    codebases = _load_codebases()
    name = (codebase or "").strip()
    if name not in codebases:
        return json.dumps(
            {
                "success": False,
                "error": "Unknown codebase.",
                "known_codebases": sorted(codebases),
            }
        )
    return json.dumps(
        {
            "success": True,
            "codebase": name,
            "repo_url": codebases[name],
        }
    )


def _codebases_path() -> Path:
    return package_dir() / "codebases.json"


def _load_codebases() -> dict[str, str]:
    with _codebases_path().open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _codebase_names() -> list[str]:
    return sorted(_load_codebases())