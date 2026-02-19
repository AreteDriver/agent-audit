"""Tests for agent_audit.linter."""

from __future__ import annotations

from agent_audit.linter import run_lint
from agent_audit.models import (
    ParsedStep,
    ParsedWorkflow,
    RuleCategory,
    Severity,
    StepType,
    WorkflowFormat,
)


def _make_workflow(**kwargs) -> ParsedWorkflow:
    defaults = {"name": "test", "format": WorkflowFormat.GORGON, "steps": []}
    defaults.update(kwargs)
    return ParsedWorkflow(**defaults)


class TestRunLint:
    def test_clean_workflow_scores_100(self) -> None:
        wf = _make_workflow(
            token_budget=100000,
            steps=[
                ParsedStep(
                    id="plan",
                    step_type=StepType.LLM,
                    role="planner",
                    estimated_tokens=5000,
                    on_failure="retry",
                    max_retries=3,
                ),
            ],
        )
        report = run_lint(wf)
        assert report.score == 100
        assert report.error_count == 0

    def test_no_budget_gets_warning(self) -> None:
        wf = _make_workflow(
            steps=[
                ParsedStep(
                    id="s1",
                    step_type=StepType.LLM,
                    estimated_tokens=5000,
                    on_failure="retry",
                    max_retries=3,
                ),
            ],
        )
        report = run_lint(wf)
        ids = [f.rule_id for f in report.findings]
        assert "B001" in ids

    def test_filter_by_category(self) -> None:
        wf = _make_workflow(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM),
            ],
        )
        report = run_lint(wf, category=RuleCategory.BUDGET)
        for finding in report.findings:
            assert finding.category == RuleCategory.BUDGET

    def test_filter_by_severity(self) -> None:
        wf = _make_workflow(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM),
            ],
        )
        report = run_lint(wf, severity=Severity.ERROR)
        for finding in report.findings:
            assert finding.severity == Severity.ERROR

    def test_score_decreases_with_findings(self) -> None:
        wf = _make_workflow(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM),
                ParsedStep(id="s2", step_type=StepType.LLM),
                ParsedStep(id="s3", step_type=StepType.LLM),
            ],
        )
        report = run_lint(wf)
        assert report.score < 100

    def test_score_floor_at_zero(self) -> None:
        # Many steps without any good practices → many findings.
        steps = [ParsedStep(id=f"s{i}", step_type=StepType.LLM) for i in range(20)]
        wf = _make_workflow(steps=steps)
        report = run_lint(wf)
        assert report.score >= 0

    def test_counts_match_findings(self) -> None:
        wf = _make_workflow(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM),
                ParsedStep(id="s2", step_type=StepType.SHELL),
            ],
        )
        report = run_lint(wf)
        assert report.error_count == sum(1 for f in report.findings if f.severity == Severity.ERROR)
        assert report.warning_count == sum(
            1 for f in report.findings if f.severity == Severity.WARNING
        )
        assert report.info_count == sum(1 for f in report.findings if f.severity == Severity.INFO)
