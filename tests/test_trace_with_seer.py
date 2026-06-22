"""Tests for trace_with_seer tool."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from seer_agent.register.tools.trace_with_seer import NAME, handler, schema
from seer_agent.register.tools import register_tools, TOOLSET_NAME


class TestSchema:
    def test_name(self) -> None:
        assert schema()["name"] == NAME

    def test_project_path_is_required(self) -> None:
        s = schema()
        assert "project_path" in s["parameters"]["required"]

    def test_optional_parameters_present(self) -> None:
        props = schema()["parameters"]["properties"]
        assert "api_key" in props
        assert "skip_build" in props
        assert "consent" in props
        assert "no_idl" in props
        assert "artifacts_path" in props

    def test_optional_parameters_not_required(self) -> None:
        required = schema()["parameters"].get("required", [])
        assert "api_key" not in required
        assert "skip_build" not in required
        assert "consent" not in required
        assert "no_idl" not in required
        assert "artifacts_path" not in required


class TestHandler:
    def _call(self, **kwargs) -> dict:
        return json.loads(handler(**kwargs))

    def test_returns_success(self) -> None:
        result = self._call(project_path="/my/project")
        assert result["success"] is True

    def test_project_path_in_response(self) -> None:
        result = self._call(project_path="/my/project")
        assert result["project_path"] == "/my/project"

    def test_workflow_name(self) -> None:
        result = self._call(project_path="/my/project")
        assert result["workflow"] == NAME

    def test_five_steps_returned(self) -> None:
        result = self._call(project_path="/my/project")
        assert len(result["steps"]) == 5

    def test_dashboard_url_present(self) -> None:
        result = self._call(project_path="/my/project")
        assert result["dashboard_url"] == "https://app.seer.run/dashboard"

    def test_notes_present_and_nonempty(self) -> None:
        result = self._call(project_path="/my/project")
        assert isinstance(result["notes"], list)
        assert len(result["notes"]) > 0

    def test_default_run_command_includes_consent(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert "--consent" in step3["command"]

    def test_skip_build_flag_included_when_true(self) -> None:
        result = self._call(project_path="/my/project", skip_build=True)
        step3 = result["steps"][2]
        assert "--skip-build" in step3["command"]

    def test_skip_build_not_included_by_default(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert "--skip-build" not in step3["command"]

    def test_no_idl_flag_included_when_true(self) -> None:
        result = self._call(project_path="/my/project", no_idl=True)
        step3 = result["steps"][2]
        assert "--no-idl" in step3["command"]

    def test_api_key_in_command_when_provided(self) -> None:
        result = self._call(project_path="/my/project", api_key="sk_test_123")
        step3 = result["steps"][2]
        assert "sk_test_123" in step3["command"]

    def test_api_key_suppresses_login_command(self) -> None:
        result = self._call(project_path="/my/project", api_key="sk_test_123")
        auth_step = result["steps"][1]
        assert auth_step["command"] is None

    def test_no_api_key_includes_login_command(self) -> None:
        result = self._call(project_path="/my/project")
        auth_step = result["steps"][1]
        assert auth_step["command"] == "seer login"

    def test_artifacts_path_in_command_when_provided(self) -> None:
        result = self._call(project_path="/my/project", artifacts_path="/custom/deploy")
        step3 = result["steps"][2]
        assert "/custom/deploy" in step3["command"]

    def test_consent_false_removes_consent_flag(self) -> None:
        result = self._call(project_path="/my/project", consent=False)
        step3 = result["steps"][2]
        assert "--consent" not in step3["command"]

    def test_step3_has_autonomous_capture_command_when_no_rpc_url(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        cap = step3["autonomous_capture_command"]
        assert cap is not None
        assert "linux" in cap
        assert "macos" in cap
        assert "script" in cap["linux"]
        assert "script" in cap["macos"]
        assert "rpc.seer.run" in cap["linux"]
        assert "SEER_RPC_URL" in cap["linux"]
        assert "after_success" in cap

    def test_step3_linux_capture_command_contains_run_command(self) -> None:
        result = self._call(project_path="/my/project")
        linux_cmd = result["steps"][2]["autonomous_capture_command"]["linux"]
        assert "seer run" in linux_cmd
        assert "--consent" in linux_cmd

    def test_step3_capture_command_has_url_not_found_guidance(self) -> None:
        result = self._call(project_path="/my/project")
        on_failure = result["steps"][2]["on_failure"]
        assert "url_not_found_in_capture" in on_failure

    def test_step3_tui_note_present_when_no_rpc_url(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert step3["tui_note"] is not None
        assert "TUI" in step3["tui_note"]

    def test_step3_session_not_provided_flag(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert step3["session_already_provided"] is False

    def test_step3_has_on_failure_guidance(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert "auth_error" in step3["on_failure"]

    def test_step4_has_test_commands(self) -> None:
        result = self._call(project_path="/my/project")
        step4 = result["steps"][3]
        assert "test_commands" in step4
        assert "native_rust" in step4["test_commands"]
        assert "anchor_typescript" in step4["test_commands"]
        assert "custom_typescript" in step4["test_commands"]

    def test_anchor_command_includes_skip_local_validator(self) -> None:
        result = self._call(project_path="/my/project")
        anchor_cmd = result["steps"][3]["test_commands"]["anchor_typescript"]["run"]
        assert "--skip-local-validator" in anchor_cmd

    def test_anchor_command_includes_skip_deploy(self) -> None:
        result = self._call(project_path="/my/project")
        anchor_cmd = result["steps"][3]["test_commands"]["anchor_typescript"]["run"]
        assert "--skip-deploy" in anchor_cmd

    def test_anchor_command_includes_cluster_url(self) -> None:
        result = self._call(project_path="/my/project")
        anchor_cmd = result["steps"][3]["test_commands"]["anchor_typescript"]["run"]
        assert "--provider.cluster" in anchor_cmd

    def test_anchor_flags_documented(self) -> None:
        result = self._call(project_path="/my/project")
        flags = result["steps"][3]["test_commands"]["anchor_typescript"]["flags"]
        assert "--skip-local-validator" in flags
        assert "--skip-deploy" in flags

    def test_native_rust_has_deploy_note(self) -> None:
        result = self._call(project_path="/my/project")
        native = result["steps"][3]["test_commands"]["native_rust"]
        assert "deploy_note" in native
        assert "pre-deployed" in native["deploy_note"]

    def test_custom_typescript_has_deploy_note(self) -> None:
        result = self._call(project_path="/my/project")
        custom = result["steps"][3]["test_commands"]["custom_typescript"]
        assert "deploy_note" in custom
        assert "pre-deployed" in custom["deploy_note"]

    def test_step4_uses_placeholder_url_when_no_rpc_url(self) -> None:
        result = self._call(project_path="/my/project")
        step4 = result["steps"][3]
        assert step4["session_url"] == "https://rpc.seer.run/<session-id>"
        assert "<session-id>" in step4["test_commands"]["anchor_typescript"]["run"]

    def test_step5_has_dashboard_url(self) -> None:
        result = self._call(project_path="/my/project")
        step5 = result["steps"][4]
        assert step5["url"] == "https://app.seer.run/dashboard"

    # --- rpc_url parameter ---

    def test_rpc_url_sets_session_already_provided(self) -> None:
        result = self._call(
            project_path="/my/project",
            rpc_url="https://rpc.seer.run/3AXR11hQSS7nNf9C3DnwkSqzDZA",
        )
        step3 = result["steps"][2]
        assert step3["session_already_provided"] is True

    def test_rpc_url_nulls_seer_run_command(self) -> None:
        result = self._call(
            project_path="/my/project",
            rpc_url="https://rpc.seer.run/3AXR11hQSS7nNf9C3DnwkSqzDZA",
        )
        step3 = result["steps"][2]
        assert step3["command"] is None

    def test_rpc_url_nulls_tui_guidance(self) -> None:
        result = self._call(
            project_path="/my/project",
            rpc_url="https://rpc.seer.run/3AXR11hQSS7nNf9C3DnwkSqzDZA",
        )
        step3 = result["steps"][2]
        assert step3["tui_note"] is None
        assert step3["autonomous_capture_command"] is None

    def test_rpc_url_injected_into_test_commands(self) -> None:
        url = "https://rpc.seer.run/3AXR11hQSS7nNf9C3DnwkSqzDZA"
        result = self._call(project_path="/my/project", rpc_url=url)
        step4 = result["steps"][3]
        assert step4["session_url"] == url
        anchor = step4["test_commands"]["anchor_typescript"]
        assert url in anchor["run"]
        assert "--skip-local-validator" in anchor["run"]
        assert "--skip-deploy" in anchor["run"]
        assert url in step4["test_commands"]["native_rust"]["setup"]
        assert url in step4["test_commands"]["custom_typescript"]["setup"]

    def test_rpc_url_strips_whitespace(self) -> None:
        url = "  https://rpc.seer.run/abc123  "
        result = self._call(project_path="/my/project", rpc_url=url)
        step4 = result["steps"][3]
        assert step4["session_url"] == url.strip()


class TestRegistration:
    def test_trace_with_seer_is_registered(self) -> None:
        ctx = MagicMock()
        register_tools(ctx)
        registered_names = [call.kwargs["name"] for call in ctx.register_tool.call_args_list]
        assert NAME in registered_names

    def test_trace_with_seer_uses_seer_agent_toolset(self) -> None:
        ctx = MagicMock()
        register_tools(ctx)
        trace_call = next(
            c for c in ctx.register_tool.call_args_list if c.kwargs["name"] == NAME
        )
        assert trace_call.kwargs["toolset"] == TOOLSET_NAME
