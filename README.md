# seer-agent

Hermes plugin for Solana codebase catalog and local clone checks.

## Layout

- `plugin.yaml` + root `__init__.py` — Hermes install entry (loads `src/seer_agent/`)
- `src/seer_agent/` — implementation package (tools, codebases.json)

## Tests

From the plugin root:

```bash
uv run pytest
```

Pytest adds `src/` to the import path only (see `pyproject.toml`), so tests use normal imports like `from seer_agent.home import …` without loading the plugin root as a flat module tree.
