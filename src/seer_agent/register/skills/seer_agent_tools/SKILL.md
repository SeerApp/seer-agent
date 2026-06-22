---
name: seer-agent-tools
description: Quick context for well-known Solana codebases and CLIs, and full transaction tracing via Seer.
version: 0.1.0
author: local
---

# Seer Agent Tools

Load with `skill_view("seer-agent:seer-agent-tools")`.

The **seer-agent** tools give quick context for well-known Solana codebases and dev CLIs, and orchestrate the full workflow for tracing Solana transactions through Seer.

## Tools

### `trace_with_seer`

**Use this when the user wants to trace or debug a Solana transaction.**

Returns a complete, ordered execution plan — prerequisites check, authentication, `seer run`, test commands, and dashboard link. Follow each step in sequence.

```
trace_with_seer(project_path="/path/to/solana-project")
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `project_path` | string | yes | Absolute path to the Solana project root (containing `Cargo.toml` or `Anchor.toml`) |
| `api_key` | string | no | Seer API key — overrides stored key and `SEER_API_KEY`. Omit if already authenticated. |
| `skip_build` | bool | no | Skip rebuild when code is unchanged (default: `false`) |
| `consent` | bool | no | Auto-approve file upload without prompt (default: `true`) |
| `no_idl` | bool | no | Skip IDL build/upload for native (non-Anchor) projects (default: `false`) |
| `artifacts_path` | string | no | Custom path to compiled `.so` artifacts if not at `./target/deploy` |

**Workflow summary (returned by the tool):**

1. **Check prerequisites** — verify `seer` CLI and Solana CLI v3+ are installed; provides install commands on failure.
2. **Authenticate** — `seer login` (once only; skip if `SEER_API_KEY` is already set or `api_key` provided).
3. **Start Seer session** — runs `seer run --consent` from the project directory; builds programs, uploads artifacts, starts a remote validator, prints the RPC URL.
4. **Run tests** — point `cargo test`, `anchor test --provider.cluster <URL>`, or a custom TS client at the session URL.
5. **View traces** — open `https://app.seer.run/dashboard` and inspect the full call stack.

**Key facts the tool reminds you about:**
- The RPC URL is derived from the API key — stable across restarts. Hardcode it in test scripts.
- Sessions time out after **30 minutes of inactivity**; restart with `seer run --skip-build`.
- Uploaded files are deleted automatically after **7 days**.
- Program IDs come from `target/deploy/<name>-keypair.json` — do not delete these files.

---

### `get_available_codebases`

List catalog repos worth cloning for reference (name, description, docs URL, git URL).

### `is_codebase_available`

Check whether a catalog repo is already cloned locally.

### `get_recommended_tools`

Check, install, and verify commands for common Solana CLIs (solana, anchor, surfpool, rust, node, yarn, jq).

---

**Always clone catalog repos under the seer-agent store** (`$HERMES_HOME/seer-agent/codebases/<name>/`). `is_codebase_available` only checks that path; clones elsewhere do not count.
