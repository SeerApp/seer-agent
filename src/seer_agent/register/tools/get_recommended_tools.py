import json

from ...recommended import recommended_tool_summaries
from ...types import JsonDict


NAME = "get_recommended_tools"


def schema() -> JsonDict:
    return {
        "name": NAME,
        "description": (
            "List recommended Solana development CLIs from the bundled catalog. "
            "Each entry includes a check command (is it installed?), a download "
            "command (install it), optional docs, and optional verify command "
            "(confirm the full toolchain after install). Run check via terminal "
            "before download; run verify after a successful install."
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
            "tools": recommended_tool_summaries(),
        }
    )
