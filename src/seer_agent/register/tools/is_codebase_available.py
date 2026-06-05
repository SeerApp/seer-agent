import json

from ...codebases import (
    catalog_names,
    codebase_git_url,
    codebase_local_path,
    codebase_store_clone_guidance,
    is_codebase_available as codebase_is_available,
    load_catalog,
    resolve_codebases_root,
)
from ...types import JsonDict


NAME = "is_codebase_available"


def schema() -> JsonDict:
    store_root = resolve_codebases_root()
    return {
        "name": NAME,
        "description": (
            f"Check whether a catalog codebase is cloned under {store_root}/<name>/ "
            f"(for example {store_root}/agave/). "
            f"{codebase_store_clone_guidance()}"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "codebase": {
                    "type": "string",
                    "enum": catalog_names(),
                    "description": (
                        "Catalog codebase name. Clone it only under "
                        f"{store_root}/<name>/ before checking availability."
                    ),
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
