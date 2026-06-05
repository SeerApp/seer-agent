---
name: seer-agent-tools
description: Quick context for well-known Solana codebases and CLIs.
version: 0.1.0
author: local
---

# Seer Agent Tools

Load with `skill_view("seer-agent:seer-agent-tools")`.

The **seer-agent** tools give quick context for well-known Solana codebases and dev CLIs. Use them to discover what exists and what is installed—not as a substitute for reading upstream docs or exploring code yourself.

- `get_available_codebases` — catalog repos worth cloning for reference
- `is_codebase_available` — whether a catalog repo is cloned locally
- `get_recommended_tools` — check, install, and verify commands for common Solana CLIs

**Always clone catalog repos under the seer-agent store** (`$HERMES_HOME/seer-agent/codebases/<name>/`). `is_codebase_available` only checks that path; clones elsewhere do not count.
