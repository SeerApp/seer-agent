# seer-agent

Hermes plugin for Seer persona routing and Solana codebase tooling.

## Tests

From the plugin root:

```bash
uv run pytest tests
```

Or from `tests/` (uses `tests/pytest.ini` as config):

```bash
cd tests && uv run pytest
```

Do not use `pythonpath = ["."]` in pytest config — the plugin root `__init__.py` uses relative imports for Hermes and must not be loaded as a test package.
