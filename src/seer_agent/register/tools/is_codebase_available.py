import json

from ...paths import (
    catalog_names,
    codebase_git_url,
    codebase_local_path,
    is_codebase_available as codebase_is_available,
    load_catalog,
)
from ...types import JsonDict


NAME = "is_codebase_available"


def schema() -> JsonDict:
    return {
        "name": NAME,
        "description": (
            "Check whether a known Solana codebase is cloned under "
            "HERMES_HOME/seer-agent/codebases/<name>/ (or SEER_CODEBASES_ROOT)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "codebase": {
                    "type": "string",
                    "enum": catalog_names(),
                    "description": "Known Solana codebase to check for local availability.",
                },
            },
            "required": ["codebase"],
        },
    }


def handler(codebase: str) -> str:
    catalog = load_catalog()
    name = (codebase or "").strip()
    if name not in catalog:
        return json.dumps(
            {
                "success": False,
                "error": "Unknown codebase.",
                "known_codebases": catalog_names(),
            }
        )
    path = codebase_local_path(name)
    available = codebase_is_available(name)
    payload: dict[str, object] = {
        "success": True,
        "codebase": name,
        "repo_url": codebase_git_url(name),
        "path": str(path),
        "available": available,
    }
    return json.dumps(payload)
