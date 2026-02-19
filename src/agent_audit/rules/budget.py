"""Budget lint rules (B001-B004)."""

from __future__ import annotations

from agent_audit.config import ROLE_TOKEN_DEFAULTS, STEP_TYPE_TOKEN_DEFAULTS
from agent_audit.models import LintFinding, ParsedWorkflow, RuleCategory, Severity, StepType
from agent_audit.rules import lint_rule


@lint_rule(
    rule_id="B001",
    category=RuleCategory.BUDGET,
    severity=Severity.WARNING,
    description="No token_budget declared at workflow level",
)
def check_workflow_budget(workflow: ParsedWorkflow) -> list[LintFinding]:
    if workflow.token_budget is None:
        return [
            LintFinding(
                rule_id="B001",
                category=RuleCategory.BUDGET,
                severity=Severity.WARNING,
                message="Workflow has no token_budget — cost risk is unbounded.",
                suggestion="Add 'token_budget: <limit>' to the workflow config.",
            )
        ]
    return []


@lint_rule(
    rule_id="B002",
    category=RuleCategory.BUDGET,
    severity=Severity.WARNING,
    description="Step estimate exceeds 50% of workflow budget",
)
def check_step_budget_hog(workflow: ParsedWorkflow) -> list[LintFinding]:
    if workflow.token_budget is None or workflow.token_budget == 0:
        return []

    findings: list[LintFinding] = []
    threshold = workflow.token_budget * 0.5

    for step in workflow.steps:
        tokens = step.estimated_tokens
        if tokens is not None and tokens > threshold:
            pct = round((tokens / workflow.token_budget) * 100)
            findings.append(
                LintFinding(
                    rule_id="B002",
                    category=RuleCategory.BUDGET,
                    severity=Severity.WARNING,
                    message=(
                        f"Step '{step.id}' uses {tokens:,} tokens ({pct}% of workflow budget)."
                    ),
                    step_id=step.id,
                    suggestion="Consider breaking this step into smaller sub-steps.",
                )
            )
    return findings


@lint_rule(
    rule_id="B003",
    category=RuleCategory.BUDGET,
    severity=Severity.ERROR,
    description="Sum of step estimates exceeds declared budget",
)
def check_total_over_budget(workflow: ParsedWorkflow) -> list[LintFinding]:
    if workflow.token_budget is None or workflow.token_budget == 0:
        return []

    total = 0
    for step in workflow.steps:
        if step.estimated_tokens is not None:
            total += step.estimated_tokens
        elif step.step_type == StepType.LLM:
            # Use archetype/default for un-declared steps.
            if step.role and step.role in ROLE_TOKEN_DEFAULTS:
                total += ROLE_TOKEN_DEFAULTS[step.role]
            else:
                total += STEP_TYPE_TOKEN_DEFAULTS.get("llm", 8000)

    if total > workflow.token_budget:
        return [
            LintFinding(
                rule_id="B003",
                category=RuleCategory.BUDGET,
                severity=Severity.ERROR,
                message=(
                    f"Estimated total ({total:,} tokens) exceeds "
                    f"workflow budget ({workflow.token_budget:,} tokens)."
                ),
                suggestion="Increase token_budget or reduce step estimates.",
            )
        ]
    return []


@lint_rule(
    rule_id="B004",
    category=RuleCategory.BUDGET,
    severity=Severity.INFO,
    description="LLM step without estimated_tokens",
)
def check_undeclared_tokens(workflow: ParsedWorkflow) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type == StepType.LLM and step.estimated_tokens is None:
            findings.append(
                LintFinding(
                    rule_id="B004",
                    category=RuleCategory.BUDGET,
                    severity=Severity.INFO,
                    message=f"Step '{step.id}' has no estimated_tokens — using defaults.",
                    step_id=step.id,
                    suggestion="Add 'estimated_tokens' to step params for accurate costing.",
                )
            )
    return findings
