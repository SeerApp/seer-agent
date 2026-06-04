import os
from pathlib import Path


def resolve_hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home()
    except Exception:
        env_home = os.environ.get("HERMES_HOME")
        if env_home:
            return Path(env_home).expanduser()
        return Path.home() / ".hermes"


def resolve_display_home(home: Path) -> str:
    try:
        from hermes_constants import display_hermes_home

        return str(display_hermes_home())
    except Exception:
        return str(home)