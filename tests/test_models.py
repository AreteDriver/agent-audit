"""Tests for agent_audit.models."""

from __future__ import annotations

from agent_audit.models import (
    CompareResult,
    LintFinding,
    LintReport,
    ModelPricing,
    ParsedStep,
    ParsedWorkflow,
    ProviderConfig,
    RuleCategory,
    Severity,
    StepEstimate,
    StepType,
    WorkflowEstimate,
    WorkflowFormat,
)


class TestWorkflowFormat:
    def test_values(self) -> None:
        assert WorkflowFormat.GORGON == "gorgon"
        assert WorkflowFormat.LANGCHAIN == "langchain"
        assert WorkflowFormat.CREWAI == "crewai"
        assert WorkflowFormat.GENERIC == "generic"

    def test_from_string(self) -> None:
        assert WorkflowFormat("gorgon") == WorkflowFormat.GORGON


class TestStepType:
    def test_values(self) -> None:
        assert StepType.LLM == "llm"
        assert StepType.SHELL == "shell"
        assert StepType.PARALLEL == "parallel"
        assert StepType.CHECKPOINT == "checkpoint"
        assert StepType.FAN_OUT == "fan_out"
        assert StepType.MAP_REDUCE == "map_reduce"

    def test_all_types_exist(self) -> None:
        expected = {
            "llm",
            "shell",
            "parallel",
            "checkpoint",
            "fan_out",
            "fan_in",
            "map_reduce",
            "branch",
            "loop",
            "mcp_tool",
        }
        assert {t.value for t in StepType} == expected


class TestSeverity:
    def test_values(self) -> None:
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"
        assert Severity.INFO == "info"


class TestRuleCategory:
    def test_values(self) -> None:
        assert RuleCategory.BUDGET == "budget"
        assert RuleCategory.RESILIENCE == "resilience"
        assert RuleCategory.EFFICIENCY == "efficiency"
        assert RuleCategory.SECURITY == "security"


class TestParsedStep:
    def test_minimal(self) -> None:
        step = ParsedStep(id="step1", step_type=StepType.LLM)
        assert step.id == "step1"
        assert step.step_type == StepType.LLM
        assert step.provider is None
        assert step.depends_on == []
        assert step.nested_steps == []

    def test_full(self) -> None:
        step = ParsedStep(
            id="build",
            step_type=StepType.LLM,
            provider="anthropic",
            model="claude-sonnet-4",
            role="builder",
            estimated_tokens=20000,
            on_failure="retry",
            max_retries=3,
            timeout_seconds=300,
            depends_on=["plan"],
            raw_params={"prompt": "Build the feature"},
        )
        assert step.provider == "anthropic"
        assert step.role == "builder"
        assert step.estimated_tokens == 20000
        assert step.depends_on == ["plan"]

    def test_nested_steps(self) -> None:
        inner = ParsedStep(id="inner1", step_type=StepType.LLM)
        outer = ParsedStep(
            id="parallel1",
            step_type=StepType.PARALLEL,
            nested_steps=[inner],
        )
        assert len(outer.nested_steps) == 1
        assert outer.nested_steps[0].id == "inner1"


class TestParsedWorkflow:
    def test_minimal(self) -> None:
        wf = ParsedWorkflow(
            name="test-workflow",
            format=WorkflowFormat.GORGON,
            steps=[ParsedStep(id="s1", step_type=StepType.LLM)],
        )
        assert wf.name == "test-workflow"
        assert wf.format == WorkflowFormat.GORGON
        assert len(wf.steps) == 1

    def test_full(self) -> None:
        wf = ParsedWorkflow(
            name="feature-build",
            version="2.0",
            description="Build a feature",
            format=WorkflowFormat.GORGON,
            token_budget=100000,
            timeout_seconds=3600,
            steps=[ParsedStep(id="s1", step_type=StepType.LLM)],
            inputs={"feature_name": {"type": "string", "required": True}},
            outputs=["result"],
            metadata={"author": "test"},
            source_path="/tmp/test.yaml",
        )
        assert wf.token_budget == 100000
        assert wf.outputs == ["result"]

    def test_serialization_round_trip(self) -> None:
        wf = ParsedWorkflow(
            name="test",
            format=WorkflowFormat.GENERIC,
            steps=[ParsedStep(id="s1", step_type=StepType.SHELL)],
        )
        data = wf.model_dump(mode="json")
        restored = ParsedWorkflow.model_validate(data)
        assert restored.name == wf.name
        assert restored.steps[0].id == "s1"


class TestStepEstimate:
    def test_creation(self) -> None:
        est = StepEstimate(
            step_id="build",
            step_type=StepType.LLM,
            provider="anthropic",
            model="claude-sonnet-4",
            role="builder",
            estimated_tokens=20000,
            input_tokens=6000,
            output_tokens=14000,
            cost_usd=0.228,
            source="archetype",
        )
        assert est.cost_usd == 0.228
        assert est.source == "archetype"


class TestWorkflowEstimate:
    def test_creation(self) -> None:
        est = WorkflowEstimate(
            workflow_name="test",
            total_tokens=20000,
            total_cost_usd=0.228,
            budget_declared=100000,
            budget_utilization=20.0,
            steps=[],
            provider="anthropic",
            model="claude-sonnet-4",
        )
        assert est.budget_utilization == 20.0


class TestLintFinding:
    def test_creation(self) -> None:
        finding = LintFinding(
            rule_id="B001",
            category=RuleCategory.BUDGET,
            severity=Severity.WARNING,
            message="No token_budget declared",
            suggestion="Add token_budget to workflow config",
        )
        assert finding.rule_id == "B001"
        assert finding.category == RuleCategory.BUDGET


class TestLintReport:
    def test_creation(self) -> None:
        report = LintReport(
            workflow_name="test",
            score=85,
            findings=[],
            error_count=0,
            warning_count=1,
            info_count=2,
        )
        assert report.score == 85

    def test_score_bounds(self) -> None:
        report = LintReport(workflow_name="test", score=0, findings=[])
        assert report.score == 0
        report = LintReport(workflow_name="test", score=100, findings=[])
        assert report.score == 100


class TestModelPricing:
    def test_creation(self) -> None:
        pricing = ModelPricing(
            name="claude-sonnet-4",
            provider="anthropic",
            input_price_per_1k=0.003,
            output_price_per_1k=0.015,
            context_window=200000,
        )
        assert pricing.input_price_per_1k == 0.003


class TestProviderConfig:
    def test_creation(self) -> None:
        model = ModelPricing(
            name="gpt-4o",
            provider="openai",
            input_price_per_1k=0.0025,
            output_price_per_1k=0.01,
        )
        config = ProviderConfig(
            name="openai",
            models={"gpt-4o": model},
            default_model="gpt-4o",
        )
        assert config.default_model == "gpt-4o"
        assert "gpt-4o" in config.models


class TestCompareResult:
    def test_creation(self) -> None:
        result = CompareResult(
            workflow_name="test",
            estimates=[],
            cheapest="ollama",
            most_expensive="anthropic",
            savings_pct=100.0,
        )
        assert result.cheapest == "ollama"
