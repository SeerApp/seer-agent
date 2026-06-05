import json

from ...paths import catalog_summaries
from ...types import JsonDict


NAME = "get_available_codebases"


def schema() -> JsonDict:
    return {
        "name": NAME,
        "description": (
            "List known Solana codebases from the bundled catalog "
            "(name, short description, docs link)."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }


def handler() -> str:
    return json.dumps(
        {
            "success": True,
            "codebases": catalog_summaries(),
        }
    )
