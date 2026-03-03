"""Lint engine: run rules and compute score."""

from __future__ import annotations

# Ensure rules are registered by importing the modules.
import agent_lint.rules.budget  # noqa: F401
import agent_lint.rules.resilience  # noqa: F401
from agent_lint.config import SEVERITY_DEDUCTIONS
from agent_lint.models import (
    LintFinding,
    LintReport,
    ParsedWorkflow,
    RuleCategory,
    Severity,
)
from agent_lint.rules import get_all_rules, get_rules_by_category


def _import_all_rules() -> None:
    """Import all rule modules to trigger registration."""
    import contextlib

    with contextlib.suppress(ImportError):
        import agent_lint.rules.efficiency  # noqa: F401
    with contextlib.suppress(ImportError):
        import agent_lint.rules.security  # noqa: F401


def run_lint(
    workflow: ParsedWorkflow,
    *,
    category: RuleCategory | None = None,
    severity: Severity | None = None,
) -> LintReport:
    """Run all lint rules against a parsed workflow."""
    _import_all_rules()

    rules = get_rules_by_category(category) if category is not None else get_all_rules()

    findings: list[LintFinding] = []
    for rule in rules:
        rule_findings = rule.func(workflow)
        findings.extend(rule_findings)

    # Filter by severity if requested.
    if severity is not None:
        findings = [f for f in findings if f.severity == severity]

    # Count by severity.
    error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
    warning_count = sum(1 for f in findings if f.severity == Severity.WARNING)
    info_count = sum(1 for f in findings if f.severity == Severity.INFO)

    # Calculate score.
    score = 100
    for finding in findings:
        score -= SEVERITY_DEDUCTIONS.get(finding.severity.value, 0)
    score = max(0, score)

    return LintReport(
        workflow_name=workflow.name,
        score=score,
        findings=findings,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
    )
