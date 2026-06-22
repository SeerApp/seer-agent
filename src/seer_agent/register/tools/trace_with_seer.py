"""trace_with_seer — full workflow plan for tracing Solana transactions via Seer."""

from __future__ import annotations

import json
from typing import Any

from ...types import JsonDict

NAME = "trace_with_seer"

_DASHBOARD_URL = "https://app.seer.run/dashboard"
_INSTALL_URL = "https://seer.run/install.sh"
_ACCOUNT_URL = "https://app.seer.run"


def schema() -> JsonDict:
    return {
        "name": NAME,
        "description": (
            "Generate a complete, step-by-step execution plan for tracing Solana "
            "transactions through Seer. Returns ordered steps with exact terminal "
            "commands, expected outputs, and troubleshooting guidance. "
            "Use this instead of manually orchestrating seer CLI commands — "
            "follow each step in sequence to build your programs, start a Seer "
            "session, run your tests against it, and view traces in the dashboard."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the Solana project root (the directory "
                        "containing Cargo.toml or Anchor.toml). All build and run "
                        "commands will be executed from this directory."
                    ),
                },
                "api_key": {
                    "type": "string",
                    "description": (
                        "Seer API key. If provided, it is passed via --api-key and "
                        "overrides any stored key or SEER_API_KEY env var. "
                        "Omit if the key is already stored or set in the environment."
                    ),
                },
                "skip_build": {
                    "type": "boolean",
                    "description": (
                        "Pass --skip-build to seer run. Default: false."
                    ),
                },
                "consent": {
                    "type": "boolean",
                    "description": (
                        "Pass --consent to seer run. Default: true."
                    ),
                },
                "no_idl": {
                    "type": "boolean",
                    "description": (
                        "Pass --no-idl to skip IDL build, discovery, and upload. "
                        "Use for native Solana projects or when IDL upload is not needed. "
                        "Default: false."
                    ),
                },
                "artifacts_path": {
                    "type": "string",
                    "description": (
                        "Custom path to the compiled artifacts directory (containing "
                        ".so, .debug, and -keypair.json files). Omit to use the "
                        "default ./target/deploy."
                    ),
                },
            },
            "required": ["project_path"],
        },
    }


def _build_run_command(
    api_key: str | None,
    skip_build: bool,
    consent: bool,
    no_idl: bool,
    artifacts_path: str | None,
) -> str:
    parts = ["seer run"]
    if consent:
        parts.append("--consent")
    if skip_build:
        parts.append("--skip-build")
    if no_idl:
        parts.append("--no-idl")
    if artifacts_path:
        parts.append(f'--artifacts "{artifacts_path}"')
    if api_key:
        parts.append(f"--api-key {api_key}")
    return " ".join(parts)


def handler(
    project_path: str,
    api_key: str | None = None,
    skip_build: bool = False,
    consent: bool = True,
    no_idl: bool = False,
    artifacts_path: str | None = None,
) -> str:
    run_command = _build_run_command(api_key, skip_build, consent, no_idl, artifacts_path)

    auth_step: dict[str, Any]
    if api_key:
        auth_step = {
            "step": 2,
            "name": "authenticate",
            "description": (
                "API key supplied directly — it will be passed via --api-key in the "
                "run command. No separate login step required."
            ),
            "command": None,
            "skip_reason": "api_key provided as tool argument",
        }
    else:
        auth_step = {
            "step": 2,
            "name": "authenticate",
            "description": (
                "Authenticate the seer CLI with your API key. "
                "Only required once — the key is stored locally. "
                "Skip this step if SEER_API_KEY is already set in your environment "
                "or if you have previously run seer login."
            ),
            "check": (
                "Check whether the key is already available: "
                "echo $SEER_API_KEY (non-empty means env var is set) "
                "or verify the config file exists at "
                "~/.config/seer/cli/api_key (Linux/macOS) / "
                "%APPDATA%\\seer\\cli\\api_key (Windows)."
            ),
            "command": "seer login",
            "command_note": (
                "Run interactively (hides input). "
                "Alternatively: seer login <YOUR_API_KEY> "
                "or set SEER_API_KEY=<YOUR_API_KEY> in the environment."
            ),
            "account_url": _ACCOUNT_URL,
            "on_failure": (
                "Create a free account and generate an API key at "
                f"{_ACCOUNT_URL}, then run seer login again."
            ),
        }

    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "name": "check_prerequisites",
            "description": (
                "Verify that the seer CLI is installed and the Solana CLI "
                "is at v3.0.0 or higher (required for cargo-build-sbf debug info)."
            ),
            "commands": [
                {
                    "run": "seer --version",
                    "purpose": "Confirm seer CLI is on PATH.",
                    "on_failure": {
                        "install_command": f"curl -fsSL {_INSTALL_URL} | sh",
                        "note": (
                            "After install, ensure $HOME/.local/bin is on your PATH. "
                            "Then reopen your shell and retry seer --version."
                        ),
                    },
                },
                {
                    "run": "solana --version",
                    "purpose": "Confirm Solana CLI is v3.0.0 or higher.",
                    "on_failure": {
                        "install_command": (
                            "curl --proto '=https' --tlsv1.2 -sSfL "
                            "https://solana-install.solana.workers.dev | bash"
                        ),
                        "note": (
                            "Seer requires Solana CLI v3+. "
                            "After install, run: solana --version to confirm."
                        ),
                    },
                },
            ],
        },
        auth_step,
        {
            "step": 3,
            "name": "start_seer_session",
            "description": (
                "From the project root, build all Solana. "
                "This is the core step — it does everything automatically."
            ),
            "cwd": project_path,
            "command": run_command,
            "what_it_does": [
                "Detects and compiles all Solana programs with debug info.",
                "Discovers IDL files (Anchor projects) unless --no-idl is set.",
                "Lists all files to be uploaded.",
                "Uploads artifacts to Seer (temporarily stored, deleted after 7 days).",
                "Starts a remote Solana validator with your programs deployed.",
                "Prints the session RPC URL.",
            ],
            "expected_output": {
                "pattern": "New Seer session at: https://rpc.seer.run/<session-id>",
                "note": (
                    "Copy this URL — it is your RPC endpoint for sending transactions. "
                    "The URL is stable across session restarts as long as your API key "
                    "does not change."
                ),
            },
            "on_failure": {
                "auth_error": (
                    "If you see 'Authentication failed', run: seer login "
                    "or set SEER_API_KEY in your environment."
                ),
                "build_error": (
                    "If programs fail to compile, check the build summary output. "
                    "Fix compilation errors then re-run the same command."
                ),
                "artifacts_error": (
                    "If artifacts directory is not found, pass --artifacts <path> "
                    "pointing to the directory containing your .so files."
                ),
                "no_programs_detected": (
                    "If 'No Solana programs detected' is printed, confirm you are "
                    "running from the project root (directory containing Cargo.toml "
                    "or Anchor.toml with program definitions)."
                ),
            },
        },
        {
            "step": 4,
            "name": "run_tests_against_session",
            "description": (
                "Point your test suite at the Seer session RPC URL from step 3. "
                "Your programs are already deployed — just direct transactions to the "
                "session URL. Everything that works with solana-test-validator works here."
            ),
            "cwd": project_path,
            "session_url_placeholder": "https://rpc.seer.run/<session-id>",
            "test_commands": {
                "native_rust": {
                    "description": "Native Solana programs with Rust tests",
                    "setup": (
                        "In your test code, replace the RpcClient URL with the session URL:\n"
                        "  let client = RpcClient::new(\"https://rpc.seer.run/<session-id>\");"
                    ),
                    "run": "cargo test",
                },
                "anchor_typescript": {
                    "description": "Anchor programs with TypeScript/Mocha tests",
                    "run": "anchor test --provider.cluster https://rpc.seer.run/<session-id>",
                    "alternative": (
                        "Or set the cluster in Anchor.toml under [provider]: "
                        "cluster = \"https://rpc.seer.run/<session-id>\""
                    ),
                },
                "custom_typescript": {
                    "description": "Custom TypeScript/JavaScript client tests",
                    "setup": (
                        "import { Connection } from \"@solana/web3.js\";\n"
                        "const connection = new Connection(\"https://rpc.seer.run/<session-id>\", \"confirmed\");"
                    ),
                    "run": "npx ts-mocha tests/**/*.ts  # or your test runner",
                },
            },
            "note": (
                "Replace <session-id> in the URL with the actual ID from step 3 output. "
                "The session timeout is 30 minutes of inactivity. "
                "If it expires, run: seer run --skip-build (from the project directory) "
                "to restart without rebuilding."
            ),
        },
        {
            "step": 5,
            "name": "view_traces_in_dashboard",
            "description": (
                "After sending transactions in step 4, open the Seer Dashboard "
                "to inspect full transaction traces. Traces appear immediately — "
                "no delay after the transaction is processed."
            ),
            "url": _DASHBOARD_URL,
            "instructions": [
                f"Open {_DASHBOARD_URL} in your browser.",
                "Find your active or recent session.",
                "Click any transaction to open its trace.",
                "Explore the full call stack: instruction flow, account changes, "
                "and source-level context mapped back to your .rs files.",
            ],
        },
    ]

    notes = [
        "The session RPC URL is derived from your API key — it stays the same "
        "across restarts as long as you use the same key. Hardcode it in test scripts.",
        "If your API key changes, the URL changes. Update any hardcoded references.",
        "Sessions shut down after 30 minutes of inactivity. Restart with: "
        "seer run --skip-build (skips rebuild when code is unchanged).",
        "Uploaded files (.so, .debug, source .rs) are stored temporarily and "
        "automatically deleted after 7 days.",
        "For CI/CD: set SEER_API_KEY as a secret env var and use seer run --consent "
        "to run non-interactively.",
        "Program IDs are derived from keypair files at "
        "target/deploy/<program-name>-keypair.json. Do not delete these files "
        "between sessions or the program ID will change.",
    ]

    return json.dumps(
        {
            "success": True,
            "workflow": NAME,
            "project_path": project_path,
            "summary": (
                "Follow steps 1–5 in order. Steps 1 and 2 are one-time setup. "
                "For subsequent traces of unchanged code, run only step 3 with "
                "--skip-build, then steps 4 and 5."
            ),
            "steps": steps,
            "dashboard_url": _DASHBOARD_URL,
            "notes": notes,
        },
        indent=2,
    )
