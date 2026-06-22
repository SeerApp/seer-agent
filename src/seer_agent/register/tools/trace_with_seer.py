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
                "rpc_url": {
                    "type": "string",
                    "description": (
                        "The Seer session RPC URL (e.g. https://rpc.seer.run/<id>). "
                        "Provide this when a session is already running — the tool will "
                        "skip the 'seer run' step entirely and go straight to test "
                        "commands using this URL. "
                        "Obtain it from: the RPC field in the seer TUI header "
                        "(press 'c' in the TUI to copy it to clipboard), or from the "
                        "SEER_RPC_URL environment variable if you exported it previously. "
                        "Since the URL is derived from your API key it is stable across "
                        "restarts — export it once and reuse it."
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
    rpc_url: str | None = None,
) -> str:
    run_command = _build_run_command(api_key, skip_build, consent, no_idl, artifacts_path)
    session_url = rpc_url.strip() if rpc_url else "https://rpc.seer.run/<session-id>"

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
            "session_already_provided": rpc_url is not None,
            "description": (
                f"Session is already running at {session_url}. "
                "Skipping seer run — proceeding directly to tests."
                if rpc_url else
                "Start a Seer session and autonomously capture the RPC URL. "
                "seer run launches an interactive TUI (via crossterm alternate-screen) "
                "so the URL is never printed to stdout. "
                "Use the autonomous_capture_command below — it runs seer via 'script' "
                "which captures raw TTY bytes to a file, then polls that file for the "
                "URL pattern and exports SEER_RPC_URL automatically."
            ),
            "cwd": project_path,
            "command": None if rpc_url else run_command,
            "autonomous_capture_command": (
                None if rpc_url else {
                    "why": (
                        "seer run uses crossterm::EnterAlternateScreen which writes "
                        "directly to the TTY — stdout pipes and redirects do not capture it. "
                        "'script' wraps the process in a pseudo-TTY and records all bytes "
                        "written to the screen, including the URL rendered by the TUI. "
                        "The URL characters themselves contain no ANSI escape sequences, "
                        "so the grep pattern matches cleanly."
                    ),
                    "linux": (
                        "SEER_CAP=$(mktemp /tmp/seer_cap.XXXXXX.txt) && "
                        f"(cd {project_path} && script -q \"$SEER_CAP\" -c '{run_command}') & "
                        "echo 'Waiting for Seer session URL...' && "
                        "for i in $(seq 1 120); do "
                        "  URL=$(grep -oP 'https://rpc\\.seer\\.run/\\S+' \"$SEER_CAP\" 2>/dev/null "
                        "        | tr -d '\\r\\n[:space:]' | head -c 100); "
                        "  if [ -n \"$URL\" ]; then "
                        "    export SEER_RPC_URL=\"$URL\"; "
                        "    echo \"SEER_RPC_URL=$URL\"; "
                        "    break; "
                        "  fi; "
                        "  sleep 1; "
                        "done; "
                        "[ -z \"$SEER_RPC_URL\" ] && echo 'ERROR: timed out waiting for RPC URL' && exit 1 || true"
                    ),
                    "macos": (
                        "SEER_CAP=$(mktemp /tmp/seer_cap.XXXXXX.txt) && "
                        f"(cd {project_path} && script -q \"$SEER_CAP\" {run_command}) & "
                        "echo 'Waiting for Seer session URL...' && "
                        "for i in $(seq 1 120); do "
                        "  URL=$(grep -oE 'https://rpc\\.seer\\.run/[A-Za-z0-9]+' \"$SEER_CAP\" 2>/dev/null "
                        "        | head -1 | tr -d '\\r\\n[:space:]'); "
                        "  if [ -n \"$URL\" ]; then "
                        "    export SEER_RPC_URL=\"$URL\"; "
                        "    echo \"SEER_RPC_URL=$URL\"; "
                        "    break; "
                        "  fi; "
                        "  sleep 1; "
                        "done; "
                        "[ -z \"$SEER_RPC_URL\" ] && echo 'ERROR: timed out waiting for RPC URL' && exit 1 || true"
                    ),
                    "after_success": (
                        "Once SEER_RPC_URL is printed, call trace_with_seer again with "
                        "rpc_url=<extracted_url> to get the test commands with the real URL. "
                        "The seer TUI keeps running in the background — do not kill it."
                    ),
                    "note_on_script_linux_syntax": (
                        "Linux script: 'script -q <file> -c <cmd>' "
                        "macOS script: 'script -q <file> <cmd>' (no -c flag). "
                        "Detect with: uname -s"
                    ),
                }
            ),
            "tui_note": (
                None if rpc_url else
                "seer run opens a terminal UI (TUI). The session URL appears in "
                "the header as: RPC  https://rpc.seer.run/<id>  (Xm Ys remaining). "
                "The autonomous_capture_command handles extraction without user interaction."
            ),
            "what_it_does": (
                [] if rpc_url else [
                    "Detects and compiles all Solana programs with debug info.",
                    "Discovers IDL files (Anchor projects) unless --no-idl is set.",
                    "Lists all files to be uploaded (.so, .debug, source .rs, IDL).",
                    "Uploads artifacts to Seer (deleted automatically after 7 days).",
                    "Starts a remote Solana validator with your programs deployed.",
                    "Opens an interactive TUI showing session status and RPC logs.",
                ]
            ),
            "on_failure": (
                {} if rpc_url else {
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
                    "url_not_found_in_capture": (
                        "If the loop times out without finding the URL, check the capture "
                        "file manually: strings $SEER_CAP | grep rpc.seer.run "
                        "If the file is empty, 'script' may not be installed — "
                        "install it with: sudo apt install bsdutils (Linux) or it is "
                        "built-in on macOS. As a fallback, run seer run --consent manually "
                        "and pass the URL via rpc_url parameter."
                    ),
                }
            ),
        },
        {
            "step": 4,
            "name": "run_tests_against_session",
            "description": (
                "Point your test suite at the Seer session RPC URL. "
                "Your programs are already deployed — just direct transactions to the "
                "session URL. Everything that works with solana-test-validator works here."
            ),
            "cwd": project_path,
            "session_url": session_url,
            "test_commands": {
                "native_rust": {
                    "description": "Native Solana programs with Rust tests",
                    "setup": (
                        "In your test code, replace the RpcClient URL with the session URL:\n"
                        f"  let client = RpcClient::new(\"{session_url}\");\n"
                        "Do NOT call solana program deploy or any programmatic deploy inside "
                        "the test — Seer already deployed your programs during seer run."
                    ),
                    "run": "cargo test",
                    "deploy_note": (
                        "Programs are pre-deployed by seer run. "
                        "Remove any deploy calls from test setup."
                    ),
                },
                "anchor_typescript": {
                    "description": "Anchor programs with TypeScript/Mocha tests",
                    "run": (
                        f"anchor test --skip-local-validator --skip-deploy "
                        f"--provider.cluster {session_url}"
                    ),
                    "flags": {
                        "--skip-local-validator": (
                            "Do not start a local solana-test-validator. "
                            "Seer's remote session is already running."
                        ),
                        "--skip-deploy": (
                            "Do not redeploy programs. "
                            "Seer already deployed them during seer run."
                        ),
                    },
                    "alternative": (
                        "Or set both flags permanently in Anchor.toml under [provider]:\n"
                        f"  cluster = \"{session_url}\"\n"
                        "  and pass --skip-local-validator --skip-deploy on every test run, "
                        "or set test.skip_local_validator = true in Anchor.toml if supported."
                    ),
                },
                "custom_typescript": {
                    "description": "Custom TypeScript/JavaScript client tests",
                    "setup": (
                        "import { Connection } from \"@solana/web3.js\";\n"
                        f"const connection = new Connection(\"{session_url}\", \"confirmed\");\n"
                        "Remove any BankrunProvider, AnchorProvider deploy(), or "
                        "programDeploy() calls from your test setup — "
                        "programs are already deployed by seer run."
                    ),
                    "run": "npx ts-mocha tests/**/*.ts  # or your test runner",
                    "deploy_note": (
                        "Programs are pre-deployed by seer run. "
                        "Do not call any deploy methods in test beforeAll/before hooks."
                    ),
                },
            },
            "note": (
                "The session timeout is 30 minutes of inactivity. "
                "If it expires, run: seer run --skip-build (from the project directory) "
                "to restart — the URL will be the same."
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
