"""Tests for agent_audit.estimator."""

from __future__ import annotations

import pytest

from agent_audit.estimator import estimate_step, estimate_workflow
from agent_audit.models import ParsedStep, ParsedWorkflow, StepType, WorkflowFormat
from agent_audit.pricing import reset_cache


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    reset_cache()


# ---------------------------------------------------------------------------
# estimate_step
# ---------------------------------------------------------------------------


class TestEstimateStep:
    def test_declared_tokens(self) -> None:
        step = ParsedStep(
            id="build",
            step_type=StepType.LLM,
            estimated_tokens=20000,
        )
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.estimated_tokens == 20000
        assert est.source == "declared"
        assert est.cost_usd > 0

    def test_archetype_tokens(self) -> None:
        step = ParsedStep(id="plan", step_type=StepType.LLM, role="planner")
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.estimated_tokens == 5000  # planner default
        assert est.source == "archetype"

    def test_default_tokens(self) -> None:
        step = ParsedStep(id="generic", step_type=StepType.LLM)
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.estimated_tokens == 8000  # llm default
        assert est.source == "default"

    def test_shell_zero_cost(self) -> None:
        step = ParsedStep(id="run", step_type=StepType.SHELL)
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.estimated_tokens == 0
        assert est.cost_usd == 0.0
        assert est.source == "default"

    def test_checkpoint_zero_cost(self) -> None:
        step = ParsedStep(id="cp", step_type=StepType.CHECKPOINT)
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.cost_usd == 0.0

    def test_input_output_split(self) -> None:
        step = ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=10000)
        est = estimate_step(step, "anthropic", "claude-sonnet-4")
        assert est.input_tokens == 3000  # 30%
        assert est.output_tokens == 7000  # 70%

    def test_free_provider(self) -> None:
        step = ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=10000)
        est = estimate_step(step, "ollama", "llama3.3-70b")
        assert est.cost_usd == 0.0
        assert est.estimated_tokens == 10000


# ---------------------------------------------------------------------------
# estimate_workflow
# ---------------------------------------------------------------------------


class TestEstimateWorkflow:
    def test_feature_build(self) -> None:
        wf = ParsedWorkflow(
            name="Feature Build",
            format=WorkflowFormat.GORGON,
            token_budget=150000,
            steps=[
                ParsedStep(
                    id="plan",
                    step_type=StepType.LLM,
                    provider="anthropic",
                    role="planner",
                    estimated_tokens=5000,
                ),
                ParsedStep(
                    id="build",
                    step_type=StepType.LLM,
                    provider="anthropic",
                    role="builder",
                    estimated_tokens=20000,
                ),
                ParsedStep(id="checkpoint", step_type=StepType.CHECKPOINT),
                ParsedStep(
                    id="test",
                    step_type=StepType.LLM,
                    provider="anthropic",
                    role="tester",
                    estimated_tokens=10000,
                ),
                ParsedStep(id="run_tests", step_type=StepType.SHELL),
                ParsedStep(
                    id="review",
                    step_type=StepType.LLM,
                    provider="anthropic",
                    role="reviewer",
                    estimated_tokens=5000,
                ),
            ],
        )
        est = estimate_workflow(wf)
        assert est.workflow_name == "Feature Build"
        assert est.total_tokens == 40000  # 5k + 20k + 0 + 10k + 0 + 5k
        assert est.total_cost_usd > 0
        assert est.budget_declared == 150000
        assert est.budget_utilization is not None
        assert est.budget_utilization < 100.0

    def test_auto_detects_provider(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GORGON,
            steps=[
                ParsedStep(
                    id="s1", step_type=StepType.LLM, provider="openai", estimated_tokens=1000
                ),
            ],
        )
        est = estimate_workflow(wf)
        assert est.provider == "openai"

    def test_explicit_provider_override(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GORGON,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=1000),
            ],
        )
        est = estimate_workflow(wf, provider="ollama", model="llama3.3-70b")
        assert est.provider == "ollama"
        assert est.total_cost_usd == 0.0

    def test_no_budget_no_utilization(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GORGON,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=1000),
            ],
        )
        est = estimate_workflow(wf)
        assert est.budget_declared is None
        assert est.budget_utilization is None

    def test_step_count_matches(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GORGON,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=1000),
                ParsedStep(id="s2", step_type=StepType.SHELL),
            ],
        )
        est = estimate_workflow(wf)
        assert len(est.steps) == 2

    def test_defaults_to_anthropic(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GENERIC,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=1000),
            ],
        )
        est = estimate_workflow(wf)
        assert est.provider == "anthropic"
