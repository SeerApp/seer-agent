"""Slash command entrypoints for seer-agent."""

from __future__ import annotations

import logging
from pathlib import Path

from .command_engine import (
    handle_slash as handle_slash_impl,
    install_or_update_soul,
    load_persona_markdown,
    render_status,
)
from ..core import operations, state
from ..router import FEATURE_DEVELOPER, PRINCIPAL_ENGINEER, PROJECT_MANAGER, route_task
from ..paths import package_dir
from ..runtime_utils import soul_path
from ..home import resolve_hermes_home, resolve_display_home
from ..types import SeerPluginContext

logger = logging.getLogger(__name__)


def _managed_block() -> str:
    return load_persona_markdown(
        plugin_dir=package_dir(),
        persona_file=state.PERSONA_FILE,
        managed_start=state.MANAGED_START,
        managed_end=state.MANAGED_END,
        logger=logger,
    )


def _soul_path() -> Path:
    return soul_path(resolve_hermes_home())


def status() -> str:
    has_repo_business_context, business_source = operations.resolve_repo_business_context()
    with state.GATE_LOCK:
        has_brief = "default" in state.BUSINESS_BRIEF
    return render_status(
        soul_path=_soul_path(),
        managed_start=state.MANAGED_START,
        managed_end=state.MANAGED_END,
        feature_developer=FEATURE_DEVELOPER,
        principal_engineer=PRINCIPAL_ENGINEER,
        project_manager=PROJECT_MANAGER,
        has_repo_business_context=has_repo_business_context,
        business_source=business_source,
        has_brief=has_brief,
    )


def handle_slash(raw_args: str, ctx: SeerPluginContext | None = None) -> str | None:
    return handle_slash_impl(
        raw_args=raw_args,
        ctx=ctx,
        feature_developer=FEATURE_DEVELOPER,
        principal_engineer=PRINCIPAL_ENGINEER,
        project_manager=PROJECT_MANAGER,
        route_task=route_task,
        delegate_to_persona=lambda persona, task, stage, call_ctx: operations.delegate_to_persona(
            persona, task=task, stage=stage, ctx=call_ctx
        ),
        refresh_business_brief_from_docs=lambda: operations.refresh_business_brief_from_docs(),
        install_or_update_soul=lambda force: install_or_update_soul(
            soul_path=_soul_path(),
            managed_block=_managed_block(),
            managed_start=state.MANAGED_START,
            managed_end=state.MANAGED_END,
            force=force,
        ),
        resolve_display_home=lambda: resolve_display_home(resolve_hermes_home()),
        status_renderer=status,
    )

