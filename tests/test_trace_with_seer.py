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

    def test_step3_has_expected_output(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert "expected_output" in step3
        assert "rpc.seer.run" in step3["expected_output"]["pattern"]

    def test_step3_has_on_failure_guidance(self) -> None:
        result = self._call(project_path="/my/project")
        step3 = result["steps"][2]
        assert "on_failure" in step3
        assert "auth_error" in step3["on_failure"]

    def test_step4_has_test_commands(self) -> None:
        result = self._call(project_path="/my/project")
        step4 = result["steps"][3]
        assert "test_commands" in step4
        assert "native_rust" in step4["test_commands"]
        assert "anchor_typescript" in step4["test_commands"]

    def test_step5_has_dashboard_url(self) -> None:
        result = self._call(project_path="/my/project")
        step5 = result["steps"][4]
        assert step5["url"] == "https://app.seer.run/dashboard"


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
