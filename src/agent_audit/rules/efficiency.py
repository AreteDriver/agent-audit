"""Efficiency lint rules (E001-E004)."""

from __future__ import annotations

from agent_audit.models import LintFinding, ParsedWorkflow, RuleCategory, Severity, StepType
from agent_audit.rules import lint_rule


@lint_rule(
    rule_id="E001",
    category=RuleCategory.EFFICIENCY,
    severity=Severity.INFO,
    description="Sequential LLM steps could be parallel",
)
def check_parallelizable(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag adjacent LLM steps with no data dependency on each other."""
    findings: list[LintFinding] = []
    llm_steps = [s for s in workflow.steps if s.step_type == StepType.LLM]

    for i in range(len(llm_steps) - 1):
        current = llm_steps[i]
        next_step = llm_steps[i + 1]

        # If next step depends on current, they can't be parallelized.
        if current.id in next_step.depends_on:
            continue

        # Check if next step references current step's outputs in raw_params.
        current_outputs = set()
        for key in ("outputs",):
            vals = current.raw_params.get(key, [])
            if isinstance(vals, list):
                current_outputs.update(str(v) for v in vals)

        # Simple heuristic: check if any output variable appears in next step's prompt.
        prompt = str(next_step.raw_params.get("prompt", ""))
        has_dependency = any(f"${{{var}}}" in prompt for var in current_outputs)

        if not has_dependency and not next_step.depends_on:
            findings.append(
                LintFinding(
                    rule_id="E001",
                    category=RuleCategory.EFFICIENCY,
                    severity=Severity.INFO,
                    message=(
                        f"Steps '{current.id}' and '{next_step.id}' appear to have "
                        f"no data dependency — consider running in parallel."
                    ),
                    step_id=next_step.id,
                    suggestion="Wrap in a 'parallel' step or add explicit depends_on.",
                )
            )

    return findings


@lint_rule(
    rule_id="E002",
    category=RuleCategory.EFFICIENCY,
    severity=Severity.WARNING,
    description="Duplicate role assignments",
)
def check_duplicate_roles(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag multiple LLM steps with the same role (possible redundancy)."""
    role_steps: dict[str, list[str]] = {}
    for step in workflow.steps:
        if step.step_type == StepType.LLM and step.role:
            role_steps.setdefault(step.role, []).append(step.id)

    findings: list[LintFinding] = []
    for role, step_ids in role_steps.items():
        if len(step_ids) > 2:
            findings.append(
                LintFinding(
                    rule_id="E002",
                    category=RuleCategory.EFFICIENCY,
                    severity=Severity.WARNING,
                    message=(
                        f"Role '{role}' is assigned to {len(step_ids)} steps "
                        f"({', '.join(step_ids)}) — possible redundancy."
                    ),
                    suggestion=f"Consider consolidating {role} steps or using different roles.",
                )
            )
    return findings


@lint_rule(
    rule_id="E003",
    category=RuleCategory.EFFICIENCY,
    severity=Severity.INFO,
    description="Unnecessary checkpoint between lightweight steps",
)
def check_lightweight_checkpoint(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag checkpoints between steps with < 5K total tokens."""
    findings: list[LintFinding] = []
    lightweight_threshold = 5000

    for i, step in enumerate(workflow.steps):
        if step.step_type != StepType.CHECKPOINT:
            continue

        # Check preceding and following steps.
        prev_tokens = 0
        next_tokens = 0

        if i > 0:
            prev = workflow.steps[i - 1]
            prev_tokens = prev.estimated_tokens or 0

        if i < len(workflow.steps) - 1:
            nxt = workflow.steps[i + 1]
            next_tokens = nxt.estimated_tokens or 0

        if prev_tokens < lightweight_threshold and next_tokens < lightweight_threshold:
            findings.append(
                LintFinding(
                    rule_id="E003",
                    category=RuleCategory.EFFICIENCY,
                    severity=Severity.INFO,
                    message=(
                        f"Checkpoint '{step.id}' is between lightweight steps — "
                        f"may add unnecessary overhead."
                    ),
                    step_id=step.id,
                    suggestion="Remove checkpoint if recovery isn't needed at this point.",
                )
            )
    return findings


@lint_rule(
    rule_id="E004",
    category=RuleCategory.EFFICIENCY,
    severity=Severity.WARNING,
    description="fan_out without max_concurrent limit",
)
def check_fan_out_no_limit(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag fan_out steps without max_concurrent."""
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type == StepType.FAN_OUT:
            max_concurrent = step.raw_params.get("max_concurrent")
            if max_concurrent is None:
                findings.append(
                    LintFinding(
                        rule_id="E004",
                        category=RuleCategory.EFFICIENCY,
                        severity=Severity.WARNING,
                        message=(
                            f"fan_out step '{step.id}' has no max_concurrent limit — "
                            f"may overwhelm resources."
                        ),
                        step_id=step.id,
                        suggestion="Add 'max_concurrent: 4' to limit parallel execution.",
                    )
                )
    return findings
