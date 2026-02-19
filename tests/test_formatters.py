"""Tests for agent_audit.formatters."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from agent_audit.formatters import (
    format_estimate_json,
    format_estimate_markdown,
    format_estimate_table,
    format_lint_json,
    format_lint_markdown,
    format_lint_table,
)
from agent_audit.models import (
    LintFinding,
    LintReport,
    RuleCategory,
    Severity,
    StepEstimate,
    StepType,
    WorkflowEstimate,
)


def _make_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, force_terminal=False), buf


def _sample_estimate() -> WorkflowEstimate:
    return WorkflowEstimate(
        workflow_name="Test Workflow",
        total_tokens=10000,
        total_cost_usd=0.12,
        budget_declared=50000,
        budget_utilization=20.0,
        steps=[
            StepEstimate(
                step_id="plan",
                step_type=StepType.LLM,
                provider="anthropic",
                model="claude-sonnet-4",
                role="planner",
                estimated_tokens=5000,
                input_tokens=1500,
                output_tokens=3500,
                cost_usd=0.06,
                source="declared",
            ),
            StepEstimate(
                step_id="run",
                step_type=StepType.SHELL,
                provider="anthropic",
                model="claude-sonnet-4",
                estimated_tokens=0,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                source="default",
            ),
        ],
        provider="anthropic",
        model="claude-sonnet-4",
    )


def _sample_lint_report() -> LintReport:
    return LintReport(
        workflow_name="Test Workflow",
        score=85,
        findings=[
            LintFinding(
                rule_id="B001",
                category=RuleCategory.BUDGET,
                severity=Severity.WARNING,
                message="No token_budget declared",
            ),
            LintFinding(
                rule_id="R001",
                category=RuleCategory.RESILIENCE,
                severity=Severity.WARNING,
                message="Step 's1' has no on_failure handler",
                step_id="s1",
            ),
        ],
        error_count=0,
        warning_count=2,
        info_count=0,
    )


class TestEstimateTable:
    def test_contains_workflow_name(self) -> None:
        c, buf = _make_console()
        format_estimate_table(_sample_estimate(), c)
        assert "Test Workflow" in buf.getvalue()

    def test_contains_total(self) -> None:
        c, buf = _make_console()
        format_estimate_table(_sample_estimate(), c)
        assert "TOTAL" in buf.getvalue()

    def test_contains_cost(self) -> None:
        c, buf = _make_console()
        format_estimate_table(_sample_estimate(), c)
        assert "$" in buf.getvalue()


class TestEstimateJson:
    def test_valid_json(self) -> None:
        c, buf = _make_console()
        format_estimate_json(_sample_estimate(), c)
        assert "total_tokens" in buf.getvalue()


class TestEstimateMarkdown:
    def test_has_table_header(self) -> None:
        c, buf = _make_console()
        format_estimate_markdown(_sample_estimate(), c)
        assert "| Step |" in buf.getvalue()


class TestLintTable:
    def test_contains_score(self) -> None:
        c, buf = _make_console()
        format_lint_table(_sample_lint_report(), c)
        assert "85" in buf.getvalue()

    def test_contains_findings(self) -> None:
        c, buf = _make_console()
        format_lint_table(_sample_lint_report(), c)
        assert "B001" in buf.getvalue()

    def test_empty_findings(self) -> None:
        report = LintReport(workflow_name="Clean", score=100, findings=[])
        c, buf = _make_console()
        format_lint_table(report, c)
        assert "No findings" in buf.getvalue()


class TestLintJson:
    def test_valid_json(self) -> None:
        c, buf = _make_console()
        format_lint_json(_sample_lint_report(), c)
        assert "score" in buf.getvalue()


class TestLintMarkdown:
    def test_has_score(self) -> None:
        c, buf = _make_console()
        format_lint_markdown(_sample_lint_report(), c)
        assert "85" in buf.getvalue()
