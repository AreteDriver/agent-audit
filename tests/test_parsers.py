"""Tests for agent_audit.parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_audit.exceptions import ParseError
from agent_audit.models import StepType, WorkflowFormat
from agent_audit.parsers import detect_format, load_yaml, parse_workflow

# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_gorgon_detected(self) -> None:
        raw = {"steps": [{"id": "s1", "type": "claude_code"}]}
        assert detect_format(raw) == WorkflowFormat.GORGON

    def test_crewai_detected(self) -> None:
        raw = {"agents": [{"role": "x"}], "tasks": [{"desc": "y"}]}
        assert detect_format(raw) == WorkflowFormat.CREWAI

    def test_langchain_nodes_detected(self) -> None:
        raw = {"nodes": [{"id": "n1"}], "edges": []}
        assert detect_format(raw) == WorkflowFormat.LANGCHAIN

    def test_langchain_metadata_detected(self) -> None:
        raw = {"steps": [], "metadata": {"framework": "langgraph"}}
        assert detect_format(raw) == WorkflowFormat.LANGCHAIN

    def test_generic_fallback(self) -> None:
        raw = {"name": "test", "steps": [{"id": "s1", "type": "custom"}]}
        assert detect_format(raw) == WorkflowFormat.GENERIC

    def test_empty_steps_is_generic(self) -> None:
        raw = {"name": "test", "steps": []}
        assert detect_format(raw) == WorkflowFormat.GENERIC

    def test_no_steps_is_generic(self) -> None:
        raw = {"name": "test"}
        assert detect_format(raw) == WorkflowFormat.GENERIC


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------


class TestLoadYaml:
    def test_valid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "test.yaml"
        p.write_text("name: test\nsteps: []", encoding="utf-8")
        raw = load_yaml(p)
        assert raw["name"] == "test"

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ParseError, match="File not found"):
            load_yaml(tmp_path / "missing.yaml")

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("{{{invalid", encoding="utf-8")
        with pytest.raises(ParseError, match="Invalid YAML"):
            load_yaml(p)

    def test_non_dict_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2", encoding="utf-8")
        with pytest.raises(ParseError, match="Expected YAML mapping"):
            load_yaml(p)


# ---------------------------------------------------------------------------
# parse_workflow — Gorgon
# ---------------------------------------------------------------------------


class TestParseGorgon:
    def test_parses_feature_build(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.name == "Feature Build"
        assert wf.format == WorkflowFormat.GORGON
        assert wf.token_budget == 150000
        assert wf.timeout_seconds == 3600
        assert len(wf.steps) == 6

    def test_step_types(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        types = [s.step_type for s in wf.steps]
        assert types == [
            StepType.LLM,  # plan
            StepType.LLM,  # build
            StepType.CHECKPOINT,  # checkpoint
            StepType.LLM,  # test
            StepType.SHELL,  # run_tests
            StepType.LLM,  # review
        ]

    def test_provider_detection(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        plan = wf.steps[0]
        assert plan.provider == "anthropic"
        shell = wf.steps[4]
        assert shell.provider is None

    def test_role_extraction(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        roles = [s.role for s in wf.steps]
        assert roles == ["planner", "builder", None, "tester", None, "reviewer"]

    def test_estimated_tokens(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.steps[0].estimated_tokens == 5000  # plan
        assert wf.steps[1].estimated_tokens == 20000  # build
        assert wf.steps[2].estimated_tokens is None  # checkpoint
        assert wf.steps[3].estimated_tokens == 10000  # test

    def test_on_failure(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.steps[0].on_failure == "abort"
        assert wf.steps[1].on_failure == "retry"
        assert wf.steps[1].max_retries == 2

    def test_condition_detected(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        review = wf.steps[5]
        assert review.has_condition is True
        plan = wf.steps[0]
        assert plan.has_condition is False

    def test_outputs(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.outputs == ["plan", "code", "review"]

    def test_inputs(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert "feature_request" in wf.inputs

    def test_metadata(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.metadata["author"] == "gorgon"

    def test_source_path(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        assert wf.source_path == str(gorgon_workflow_path)


class TestParseGorgonNoBudget:
    def test_no_budget(self, gorgon_no_budget_path: Path) -> None:
        wf = parse_workflow(gorgon_no_budget_path)
        assert wf.token_budget is None
        assert len(wf.steps) == 2

    def test_no_estimated_tokens(self, gorgon_no_budget_path: Path) -> None:
        wf = parse_workflow(gorgon_no_budget_path)
        for step in wf.steps:
            assert step.estimated_tokens is None


# ---------------------------------------------------------------------------
# parse_workflow — Generic
# ---------------------------------------------------------------------------


class TestParseGeneric:
    def test_parses_generic(self, generic_path: Path) -> None:
        wf = parse_workflow(generic_path)
        assert wf.format == WorkflowFormat.GENERIC
        assert wf.name == "Simple Pipeline"
        assert len(wf.steps) == 2

    def test_step_types_guessed(self, generic_path: Path) -> None:
        wf = parse_workflow(generic_path)
        # Both steps have 'prompt' → guessed as LLM.
        for step in wf.steps:
            assert step.step_type == StepType.LLM
