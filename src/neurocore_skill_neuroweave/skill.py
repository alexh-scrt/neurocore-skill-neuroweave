"""NeuroWeave skill — knowledge graph memory for NeuroCore agents.

Wraps NeuroWeave's async API as a sync FlowEngine Skill with three modes:

- **process**: Extract knowledge from a message, update the graph.
  Consumes: ``message`` → Provides: ``neuroweave_result``
- **query**: Query the knowledge graph for relevant context.
  Consumes: ``query`` → Provides: ``neuroweave_result``
- **context**: Extract + query in one step (default).
  Consumes: ``message`` → Provides: ``neuroweave_result``, ``neuroweave_context``

The async NeuroWeave API is bridged to sync via ``asyncio.run()``.
The NeuroWeave instance is created on ``init(config)`` and started
lazily on the first ``process()`` call.

Config keys (passed via neurocore.yaml or blueprint):
    mode: str — "process", "query", or "context" (default: "context")
    llm_provider: str — "mock", "anthropic", or "openai" (default: "mock")
    llm_model: str — LLM model identifier
    llm_api_key: str — API key (or set via ANTHROPIC_API_KEY env)
    enable_visualization: bool — start the graph viz server (default: false)
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from flowengine import FlowContext

from neurocore.skills.base import Skill, SkillMeta


class NeuroWeaveSkill(Skill):
    """Knowledge graph memory skill powered by NeuroWeave.

    Bridges NeuroWeave's async API into NeuroCore's synchronous
    FlowEngine execution model. Manages a persistent NeuroWeave
    instance across the skill lifecycle.
    """

    skill_meta: ClassVar[SkillMeta] = SkillMeta(
        name="neuroweave",
        version="0.1.0",
        description="Real-time knowledge graph memory for agentic AI",
        author="NeuroCore Contributors",
        requires=["neuroweave>=0.1.0"],
        provides=["neuroweave_result", "neuroweave_context"],
        consumes=["message", "query"],
        config_schema={
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "Operation mode: process, query, or context",
                },
                "llm_provider": {
                    "type": "string",
                    "description": "LLM provider: mock, anthropic, or openai",
                },
                "llm_model": {
                    "type": "string",
                    "description": "LLM model identifier",
                },
                "llm_api_key": {
                    "type": "string",
                    "description": "LLM API key",
                },
                "enable_visualization": {
                    "type": "boolean",
                    "description": "Start graph visualization server",
                },
            },
        },
        tags=["memory", "knowledge-graph", "llm"],
    )

    _nw: Any  # NeuroWeave instance (typed as Any to avoid import at module level)
    _started: bool

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self._nw = None
        self._started = False

    def init(self, config: dict[str, Any]) -> None:
        """Initialize the skill and create (but don't start) the NeuroWeave instance."""
        super().init(config)

        # Import NeuroWeave lazily so the skill can be registered
        # even if NeuroWeave isn't installed (graceful degradation).
        from neuroweave import NeuroWeave

        nw_kwargs: dict[str, Any] = {}

        if "llm_provider" in config:
            nw_kwargs["llm_provider"] = config["llm_provider"]
        if "llm_model" in config:
            nw_kwargs["llm_model"] = config["llm_model"]
        if "llm_api_key" in config:
            nw_kwargs["llm_api_key"] = config["llm_api_key"]

        nw_kwargs["enable_visualization"] = config.get(
            "enable_visualization", False
        )

        self._nw = NeuroWeave(**nw_kwargs)

    def _ensure_started(self) -> None:
        """Start the NeuroWeave instance if not already running."""
        if not self._started and self._nw is not None:
            asyncio.run(self._nw.start())
            self._started = True

    def setup(self, context: FlowContext) -> None:
        """Start NeuroWeave on the first run."""
        self._ensure_started()

    def process(self, context: FlowContext) -> FlowContext:
        """Execute the NeuroWeave operation based on configured mode.

        Args:
            context: FlowContext with input data.

        Returns:
            FlowContext with neuroweave results.
        """
        self._ensure_started()
        mode = self.config.get("mode", "context")

        if mode == "process":
            self._do_process(context)
        elif mode == "query":
            self._do_query(context)
        elif mode == "context":
            self._do_context(context)
        else:
            # Default to context mode for unknown modes
            self._do_context(context)

        return context

    def _do_process(self, context: FlowContext) -> None:
        """Extract knowledge from message, update graph."""
        message = context.get("message", "")
        if not message:
            context.set("neuroweave_result", {"error": "No message provided"})
            return

        result = asyncio.run(self._nw.process(message))
        context.set("neuroweave_result", result.to_dict())

    def _do_query(self, context: FlowContext) -> None:
        """Query the knowledge graph."""
        query_text = context.get("query", "")
        if not query_text:
            context.set("neuroweave_result", {"error": "No query provided"})
            return

        result = asyncio.run(self._nw.query(query_text))
        context.set("neuroweave_result", result.to_dict())

    def _do_context(self, context: FlowContext) -> None:
        """Process message AND query for relevant context."""
        message = context.get("message", "")
        if not message:
            context.set("neuroweave_result", {"error": "No message provided"})
            return

        result = asyncio.run(self._nw.get_context(message))
        context.set("neuroweave_result", result.process.to_dict())
        context.set("neuroweave_context", result.relevant.to_dict())

    def teardown(self, context: FlowContext) -> None:
        """Stop the NeuroWeave instance."""
        if self._started and self._nw is not None:
            try:
                asyncio.run(self._nw.stop())
            except Exception:
                pass  # Best-effort cleanup
            self._started = False

    def health_check(self) -> bool:
        """Check if NeuroWeave is operational."""
        return self.is_initialized and self._nw is not None
