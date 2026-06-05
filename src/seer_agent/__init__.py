"""seer-agent plugin implementation."""

from __future__ import annotations

import logging

from .register import register_tools
from .types import SeerPluginContext

logger = logging.getLogger(__name__)


def register(ctx: SeerPluginContext) -> None:
    """Hermes plugin entrypoint."""
    logger.info("seer-agent plugin loaded")
    register_tools(ctx)
