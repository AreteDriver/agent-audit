"""Security lint rules (S001-S004)."""

from __future__ import annotations

import re

from agent_audit.models import LintFinding, ParsedWorkflow, RuleCategory, Severity, StepType
from agent_audit.rules import lint_rule

# Pattern for variable interpolation in shell commands.
_SHELL_VAR_PATTERN = re.compile(r"\$\{[^}]+\}")

# Pattern for hardcoded absolute paths.
_HARDCODED_PATH_PATTERN = re.compile(r"(?:/usr/|/home/|/etc/|/var/|/opt/|C:\\)")


@lint_rule(
    rule_id="S001",
    category=RuleCategory.SECURITY,
    severity=Severity.ERROR,
    description="Shell step with variable interpolation (command injection risk)",
)
def check_shell_injection(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag shell steps that use ${var} interpolation."""
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type != StepType.SHELL:
            continue
        command = str(step.raw_params.get("command", ""))
        if _SHELL_VAR_PATTERN.search(command):
            findings.append(
                LintFinding(
                    rule_id="S001",
                    category=RuleCategory.SECURITY,
                    severity=Severity.ERROR,
                    message=(
                        f"Shell step '{step.id}' uses variable interpolation in command — "
                        f"potential command injection risk."
                    ),
                    step_id=step.id,
                    suggestion="Validate inputs or use parameterized execution.",
                )
            )
    return findings


@lint_rule(
    rule_id="S002",
    category=RuleCategory.SECURITY,
    severity=Severity.WARNING,
    description="Hardcoded paths in shell commands",
)
def check_hardcoded_paths(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag shell steps with hardcoded absolute paths."""
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type != StepType.SHELL:
            continue
        command = str(step.raw_params.get("command", ""))
        if _HARDCODED_PATH_PATTERN.search(command):
            findings.append(
                LintFinding(
                    rule_id="S002",
                    category=RuleCategory.SECURITY,
                    severity=Severity.WARNING,
                    message=(
                        f"Shell step '{step.id}' contains hardcoded paths — may not be portable."
                    ),
                    step_id=step.id,
                    suggestion="Use input variables or environment variables for paths.",
                )
            )
    return findings


@lint_rule(
    rule_id="S003",
    category=RuleCategory.SECURITY,
    severity=Severity.INFO,
    description="No input validation on required inputs",
)
def check_input_validation(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag workflows with required inputs that have no type validation."""
    if not workflow.inputs:
        return []

    findings: list[LintFinding] = []
    for name, config in workflow.inputs.items():
        if not isinstance(config, dict):
            continue
        is_required = config.get("required", False)
        has_type = "type" in config
        if is_required and not has_type:
            findings.append(
                LintFinding(
                    rule_id="S003",
                    category=RuleCategory.SECURITY,
                    severity=Severity.INFO,
                    message=f"Required input '{name}' has no type constraint.",
                    suggestion=f"Add 'type: string' (or appropriate type) to input '{name}'.",
                )
            )
    return findings


@lint_rule(
    rule_id="S004",
    category=RuleCategory.SECURITY,
    severity=Severity.WARNING,
    description="MCP tool step without server validation",
)
def check_mcp_no_server(workflow: ParsedWorkflow) -> list[LintFinding]:
    """Flag mcp_tool steps that don't specify a server."""
    findings: list[LintFinding] = []
    for step in workflow.steps:
        if step.step_type != StepType.MCP_TOOL:
            continue
        server = step.raw_params.get("server")
        if not server:
            findings.append(
                LintFinding(
                    rule_id="S004",
                    category=RuleCategory.SECURITY,
                    severity=Severity.WARNING,
                    message=(
                        f"MCP tool step '{step.id}' has no server specified — "
                        f"tool resolution may be ambiguous."
                    ),
                    step_id=step.id,
                    suggestion="Add 'server: <name>' to specify which MCP server to use.",
                )
            )
    return findings
