"""Tests for NeuroWeave skill wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore_skill_neuroweave.skill import NeuroWeaveSkill


# --- Mock result types ---


@dataclass
class MockProcessResult:
    nodes_added: int = 2
    edges_added: int = 1
    edges_skipped: int = 0
    entity_count: int = 2
    relation_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities_extracted": self.entity_count,
            "relations_extracted": self.relation_count,
            "nodes_added": self.nodes_added,
            "edges_added": self.edges_added,
        }


@dataclass
class MockQueryResult:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}


@dataclass
class MockContextResult:
    process: MockProcessResult = field(default_factory=MockProcessResult)
    relevant: MockQueryResult = field(default_factory=MockQueryResult)
    plan: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "process": self.process.to_dict(),
            "relevant": self.relevant.to_dict(),
            "plan": None,
        }


# --- Fixtures ---


@pytest.fixture
def mock_neuroweave():
    """Create a mock NeuroWeave instance."""
    nw = MagicMock()
    nw.start = AsyncMock()
    nw.stop = AsyncMock()
    nw.process = AsyncMock(return_value=MockProcessResult())
    nw.query = AsyncMock(
        return_value=MockQueryResult(
            nodes=[{"id": "1", "name": "Lena"}],
            edges=[],
        )
    )
    nw.get_context = AsyncMock(
        return_value=MockContextResult(
            relevant=MockQueryResult(
                nodes=[{"id": "1", "name": "Lena"}],
                edges=[],
            )
        )
    )
    return nw


@pytest.fixture
def skill(mock_neuroweave):
    """Create a NeuroWeaveSkill with mocked NeuroWeave."""
    with patch(
        "neurocore_skill_neuroweave.skill.NeuroWeaveSkill._ensure_started"
    ):
        s = NeuroWeaveSkill()
        s.init({"mode": "context", "llm_provider": "mock"})
        s._nw = mock_neuroweave
        s._started = True
    return s


# --- SkillMeta tests ---


class TestSkillMeta:
    def test_name(self):
        assert NeuroWeaveSkill.skill_meta.name == "neuroweave"

    def test_version(self):
        assert NeuroWeaveSkill.skill_meta.version == "0.1.0"

    def test_provides(self):
        assert "neuroweave_result" in NeuroWeaveSkill.skill_meta.provides
        assert "neuroweave_context" in NeuroWeaveSkill.skill_meta.provides

    def test_consumes(self):
        assert "message" in NeuroWeaveSkill.skill_meta.consumes
        assert "query" in NeuroWeaveSkill.skill_meta.consumes

    def test_tags(self):
        assert "memory" in NeuroWeaveSkill.skill_meta.tags
        assert "knowledge-graph" in NeuroWeaveSkill.skill_meta.tags

    def test_requires(self):
        assert "neuroweave>=0.1.0" in NeuroWeaveSkill.skill_meta.requires


# --- Process mode tests ---


class TestProcessMode:
    def test_extracts_and_sets_result(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = True
        s.init({"mode": "process", "llm_provider": "mock"})
        # Re-assign since init() overwrites _nw
        s._nw = mock_neuroweave
        s._started = True

        ctx = FlowContext()
        ctx.set("message", "My wife Lena loves sushi")
        result = s.process(ctx)

        mock_neuroweave.process.assert_called_once_with("My wife Lena loves sushi")
        nw_result = result.get("neuroweave_result")
        assert nw_result.nodes_added == 2

    def test_empty_message_sets_error(self, skill):
        skill.init({"mode": "process", "llm_provider": "mock"})
        skill._started = True

        ctx = FlowContext()
        result = skill.process(ctx)
        assert "error" in result.get("neuroweave_result")


# --- Query mode tests ---


class TestQueryMode:
    def test_queries_and_sets_result(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = True
        s.init({"mode": "query", "llm_provider": "mock"})
        s._nw = mock_neuroweave
        s._started = True

        ctx = FlowContext()
        ctx.set("query", "What does Lena like?")
        result = s.process(ctx)

        mock_neuroweave.query.assert_called_once_with("What does Lena like?")
        nw_result = result.get("neuroweave_result")
        assert len(nw_result.nodes) == 1

    def test_empty_query_sets_error(self, skill):
        skill.init({"mode": "query", "llm_provider": "mock"})
        skill._started = True

        ctx = FlowContext()
        result = skill.process(ctx)
        assert "error" in result.get("neuroweave_result")


# --- Context mode tests ---


class TestContextMode:
    def test_processes_and_queries(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = True
        s.init({"mode": "context", "llm_provider": "mock"})
        s._nw = mock_neuroweave
        s._started = True

        ctx = FlowContext()
        ctx.set("message", "My wife Lena loves sushi")
        result = s.process(ctx)

        mock_neuroweave.get_context.assert_called_once_with(
            "My wife Lena loves sushi"
        )
        nw_result = result.get("neuroweave_result")
        assert nw_result.nodes_added == 2
        nw_context = result.get("neuroweave_context")
        assert hasattr(nw_context, "nodes")

    def test_default_mode_is_context(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = True
        s.init({"llm_provider": "mock"})  # no mode specified
        s._nw = mock_neuroweave
        s._started = True

        ctx = FlowContext()
        ctx.set("message", "test")
        s.process(ctx)

        mock_neuroweave.get_context.assert_called_once()

    def test_empty_message_sets_error(self, skill):
        skill.init({"mode": "context", "llm_provider": "mock"})
        skill._started = True

        ctx = FlowContext()
        result = skill.process(ctx)
        assert "error" in result.get("neuroweave_result")


# --- Lifecycle tests ---


class TestLifecycle:
    def test_health_check_before_init(self):
        s = NeuroWeaveSkill()
        assert not s.health_check()

    def test_health_check_after_init(self):
        with patch("neurocore_skill_neuroweave.skill.NeuroWeaveSkill._ensure_started"):
            s = NeuroWeaveSkill()
            s.init({"llm_provider": "mock"})
            assert s.health_check()

    def test_teardown_stops_neuroweave(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = True

        ctx = FlowContext()
        s.teardown(ctx)

        mock_neuroweave.stop.assert_called_once()
        assert not s._started

    def test_teardown_idempotent(self, mock_neuroweave):
        s = NeuroWeaveSkill()
        s._nw = mock_neuroweave
        s._started = False  # not started

        ctx = FlowContext()
        s.teardown(ctx)

        mock_neuroweave.stop.assert_not_called()
