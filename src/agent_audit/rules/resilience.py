"""Resilience lint rules (R001-R005)."""

from __future__ import annotations

from agent_audit.config import ROLE_TOKEN_DEFAULTS, STEP_TYPE_TOKEN_DEFAULTS
from agent_audit.models import LintFinding, ParsedWorkflow, RuleCategory, Severity, StepType
from agent_audit.rules import lint_rule


@lint_rule(
    rule_id="R001",
    category=RuleCategory.RESILIENCE,
    severity=Severity.WARNING,
    description="LLM step has no on_failure handler",
)
def check_missing_on_failure(workflow: ParsedWorkflow) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type == StepType.LLM and step.on_failure is None:
            findings.append(
                LintFinding(
                    rule_id="R001",
                    category=RuleCategory.RESILIENCE,
                    severity=Severity.WARNING,
                    message=f"Step '{step.id}' has no on_failure handler.",
                    step_id=step.id,
                    suggestion="Add 'on_failure: retry' or 'on_failure: skip' to handle errors.",
                )
            )
    return findings


@lint_rule(
    rule_id="R002",
    category=RuleCategory.RESILIENCE,
    severity=Severity.WARNING,
    description="on_failure: abort with no fallback",
)
def check_abort_no_fallback(workflow: ParsedWorkflow) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.on_failure == "abort" and not step.has_fallback:
            findings.append(
                LintFinding(
                    rule_id="R002",
                    category=RuleCategory.RESILIENCE,
                    severity=Severity.WARNING,
                    message=(
                        f"Step '{step.id}' uses on_failure: abort "
                        f"without a fallback — workflow will halt on any error."
                    ),
                    step_id=step.id,
                    suggestion="Add a 'fallback' config or use 'on_failure: retry'.",
                )
            )
    return findings


@lint_rule(
    rule_id="R003",
    category=RuleCategory.RESILIENCE,
    severity=Severity.INFO,
    description="retry without max_retries",
)
def check_retry_no_max(workflow: ParsedWorkflow) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.on_failure == "retry" and step.max_retries == 0:
            findings.append(
                LintFinding(
                    rule_id="R003",
                    category=RuleCategory.RESILIENCE,
                    severity=Severity.INFO,
                    message=(
                        f"Step '{step.id}' has on_failure: retry but max_retries is 0 (unbounded)."
                    ),
                    step_id=step.id,
                    suggestion="Set 'max_retries: 3' to prevent infinite retry loops.",
                )
            )
    return findings


@lint_rule(
    rule_id="R004",
    category=RuleCategory.RESILIENCE,
    severity=Severity.WARNING,
    description="Shell step without timeout",
)
def check_shell_no_timeout(workflow: ParsedWorkflow) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type == StepType.SHELL and step.timeout_seconds is None:
            findings.append(
                LintFinding(
                    rule_id="R004",
                    category=RuleCategory.RESILIENCE,
                    severity=Severity.WARNING,
                    message=f"Shell step '{step.id}' has no timeout — may run indefinitely.",
                    step_id=step.id,
                    suggestion="Add 'timeout_seconds: 300' to prevent hung processes.",
                )
            )
    return findings


@lint_rule(
    rule_id="R005",
    category=RuleCategory.RESILIENCE,
    severity=Severity.INFO,
    description="No checkpoint between expensive step groups",
)
def check_missing_checkpoint(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag if there are 3+ consecutive LLM steps with no checkpoint."""
    consecutive_llm = 0
    expensive_tokens = 0
    threshold = 30000  # Flag if >30K tokens without checkpoint.

    for step in workflow.steps:
        if step.step_type == StepType.LLM:
            consecutive_llm += 1
            tokens = step.estimated_tokens
            if tokens is None:
                if step.role and step.role in ROLE_TOKEN_DEFAULTS:
                    tokens = ROLE_TOKEN_DEFAULTS[step.role]
                else:
                    tokens = STEP_TYPE_TOKEN_DEFAULTS.get("llm", 8000)
            expensive_tokens += tokens
        elif step.step_type == StepType.CHECKPOINT:
            consecutive_llm = 0
            expensive_tokens = 0
        else:
            # Non-LLM, non-checkpoint steps don't reset the counter.
            pass

        if consecutive_llm >= 3 and expensive_tokens >= threshold:
            return [
                LintFinding(
                    rule_id="R005",
                    category=RuleCategory.RESILIENCE,
                    severity=Severity.INFO,
                    message=(
                        f"{consecutive_llm} consecutive LLM steps "
                        f"({expensive_tokens:,} tokens) without a checkpoint."
                    ),
                    suggestion="Add a checkpoint step between expensive groups for recovery.",
                )
            ]

    return []
