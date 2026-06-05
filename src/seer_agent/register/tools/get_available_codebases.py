import json

from ...paths import catalog_names
from ...types import JsonDict


NAME = "get_available_codebases"


def schema() -> JsonDict:
    return {
        "name": NAME,
        "description": "List known Solana codebase names from the bundled catalog.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }


def handler() -> str:
    return json.dumps(
        {
            "success": True,
            "codebases": catalog_names(),
        }
    )
