"""Tests for individual lint rules."""

from __future__ import annotations

from agent_audit.models import (
    ParsedStep,
    ParsedWorkflow,
    Severity,
    StepType,
    WorkflowFormat,
)
from agent_audit.rules.budget import (
    check_step_budget_hog,
    check_total_over_budget,
    check_undeclared_tokens,
    check_workflow_budget,
)
from agent_audit.rules.efficiency import (
    check_duplicate_roles,
    check_fan_out_no_limit,
    check_lightweight_checkpoint,
    check_parallelizable,
)
from agent_audit.rules.resilience import (
    check_abort_no_fallback,
    check_missing_checkpoint,
    check_missing_on_failure,
    check_retry_no_max,
    check_shell_no_timeout,
)
from agent_audit.rules.security import (
    check_hardcoded_paths,
    check_input_validation,
    check_mcp_no_server,
    check_shell_injection,
)


def _wf(**kwargs) -> ParsedWorkflow:
    defaults = {"name": "test", "format": WorkflowFormat.GORGON, "steps": []}
    defaults.update(kwargs)
    return ParsedWorkflow(**defaults)


# ---------------------------------------------------------------------------
# Budget rules
# ---------------------------------------------------------------------------


class TestB001WorkflowBudget:
    def test_no_budget_flags(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.LLM)])
        findings = check_workflow_budget(wf)
        assert len(findings) == 1
        assert findings[0].rule_id == "B001"

    def test_with_budget_clean(self) -> None:
        wf = _wf(token_budget=100000, steps=[])
        assert check_workflow_budget(wf) == []


class TestB002StepBudgetHog:
    def test_hog_detected(self) -> None:
        wf = _wf(
            token_budget=100000,
            steps=[ParsedStep(id="big", step_type=StepType.LLM, estimated_tokens=60000)],
        )
        findings = check_step_budget_hog(wf)
        assert len(findings) == 1
        assert findings[0].step_id == "big"

    def test_under_threshold_clean(self) -> None:
        wf = _wf(
            token_budget=100000,
            steps=[ParsedStep(id="ok", step_type=StepType.LLM, estimated_tokens=40000)],
        )
        assert check_step_budget_hog(wf) == []

    def test_no_budget_skips(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=60000)],
        )
        assert check_step_budget_hog(wf) == []


class TestB003TotalOverBudget:
    def test_over_budget(self) -> None:
        wf = _wf(
            token_budget=10000,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=6000),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=6000),
            ],
        )
        findings = check_total_over_budget(wf)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_under_budget_clean(self) -> None:
        wf = _wf(
            token_budget=100000,
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=5000)],
        )
        assert check_total_over_budget(wf) == []

    def test_undeclared_tokens_use_defaults(self) -> None:
        # Two LLM steps without tokens → uses role/type defaults.
        wf = _wf(
            token_budget=100,
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="builder"),  # 20000 default
            ],
        )
        findings = check_total_over_budget(wf)
        assert len(findings) == 1


class TestB004UndeclaredTokens:
    def test_undeclared_flagged(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.LLM)])
        findings = check_undeclared_tokens(wf)
        assert len(findings) == 1
        assert findings[0].rule_id == "B004"

    def test_declared_clean(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=5000)],
        )
        assert check_undeclared_tokens(wf) == []

    def test_shell_not_flagged(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.SHELL)])
        assert check_undeclared_tokens(wf) == []


# ---------------------------------------------------------------------------
# Resilience rules
# ---------------------------------------------------------------------------


class TestR001MissingOnFailure:
    def test_no_handler_flagged(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.LLM)])
        findings = check_missing_on_failure(wf)
        assert len(findings) == 1

    def test_with_handler_clean(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, on_failure="retry")],
        )
        assert check_missing_on_failure(wf) == []

    def test_shell_not_flagged(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.SHELL)])
        assert check_missing_on_failure(wf) == []


class TestR002AbortNoFallback:
    def test_abort_no_fallback_flagged(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, on_failure="abort")],
        )
        findings = check_abort_no_fallback(wf)
        assert len(findings) == 1

    def test_abort_with_fallback_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="s1",
                    step_type=StepType.LLM,
                    on_failure="abort",
                    has_fallback=True,
                ),
            ],
        )
        assert check_abort_no_fallback(wf) == []

    def test_retry_not_flagged(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.LLM, on_failure="retry")],
        )
        assert check_abort_no_fallback(wf) == []


class TestR003RetryNoMax:
    def test_retry_no_max_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, on_failure="retry", max_retries=0),
            ],
        )
        findings = check_retry_no_max(wf)
        assert len(findings) == 1

    def test_retry_with_max_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, on_failure="retry", max_retries=3),
            ],
        )
        assert check_retry_no_max(wf) == []


class TestR004ShellNoTimeout:
    def test_no_timeout_flagged(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.SHELL)])
        findings = check_shell_no_timeout(wf)
        assert len(findings) == 1

    def test_with_timeout_clean(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="s1", step_type=StepType.SHELL, timeout_seconds=300)],
        )
        assert check_shell_no_timeout(wf) == []


class TestR005MissingCheckpoint:
    def test_many_llm_steps_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=15000),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=15000),
                ParsedStep(id="s3", step_type=StepType.LLM, estimated_tokens=15000),
            ],
        )
        findings = check_missing_checkpoint(wf)
        assert len(findings) == 1

    def test_checkpoint_breaks_chain(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=15000),
                ParsedStep(id="cp", step_type=StepType.CHECKPOINT),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=15000),
                ParsedStep(id="s3", step_type=StepType.LLM, estimated_tokens=15000),
            ],
        )
        findings = check_missing_checkpoint(wf)
        assert len(findings) == 0

    def test_few_steps_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=5000),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=5000),
            ],
        )
        assert check_missing_checkpoint(wf) == []


# ---------------------------------------------------------------------------
# Efficiency rules
# ---------------------------------------------------------------------------


class TestE001Parallelizable:
    def test_independent_steps_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="reviewer"),
                ParsedStep(id="s2", step_type=StepType.LLM, role="reviewer"),
            ],
        )
        findings = check_parallelizable(wf)
        assert len(findings) == 1

    def test_dependent_steps_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="planner"),
                ParsedStep(
                    id="s2",
                    step_type=StepType.LLM,
                    role="builder",
                    depends_on=["s1"],
                ),
            ],
        )
        assert check_parallelizable(wf) == []

    def test_single_step_clean(self) -> None:
        wf = _wf(steps=[ParsedStep(id="s1", step_type=StepType.LLM)])
        assert check_parallelizable(wf) == []


class TestE002DuplicateRoles:
    def test_many_same_role_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="reviewer"),
                ParsedStep(id="s2", step_type=StepType.LLM, role="reviewer"),
                ParsedStep(id="s3", step_type=StepType.LLM, role="reviewer"),
            ],
        )
        findings = check_duplicate_roles(wf)
        assert len(findings) == 1

    def test_two_same_role_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="reviewer"),
                ParsedStep(id="s2", step_type=StepType.LLM, role="reviewer"),
            ],
        )
        # Two is fine (e.g., security + quality review).
        assert check_duplicate_roles(wf) == []

    def test_different_roles_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, role="planner"),
                ParsedStep(id="s2", step_type=StepType.LLM, role="builder"),
                ParsedStep(id="s3", step_type=StepType.LLM, role="tester"),
            ],
        )
        assert check_duplicate_roles(wf) == []


class TestE003LightweightCheckpoint:
    def test_lightweight_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=2000),
                ParsedStep(id="cp", step_type=StepType.CHECKPOINT),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=2000),
            ],
        )
        findings = check_lightweight_checkpoint(wf)
        assert len(findings) == 1

    def test_expensive_checkpoint_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(id="s1", step_type=StepType.LLM, estimated_tokens=20000),
                ParsedStep(id="cp", step_type=StepType.CHECKPOINT),
                ParsedStep(id="s2", step_type=StepType.LLM, estimated_tokens=10000),
            ],
        )
        assert check_lightweight_checkpoint(wf) == []


class TestE004FanOutNoLimit:
    def test_no_limit_flagged(self) -> None:
        wf = _wf(
            steps=[ParsedStep(id="fo", step_type=StepType.FAN_OUT, raw_params={})],
        )
        findings = check_fan_out_no_limit(wf)
        assert len(findings) == 1

    def test_with_limit_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="fo",
                    step_type=StepType.FAN_OUT,
                    raw_params={"max_concurrent": 4},
                ),
            ],
        )
        assert check_fan_out_no_limit(wf) == []


# ---------------------------------------------------------------------------
# Security rules
# ---------------------------------------------------------------------------


class TestS001ShellInjection:
    def test_interpolation_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="run",
                    step_type=StepType.SHELL,
                    raw_params={"command": "cd ${path} && make"},
                ),
            ],
        )
        findings = check_shell_injection(wf)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_no_interpolation_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="run",
                    step_type=StepType.SHELL,
                    raw_params={"command": "pytest tests/"},
                ),
            ],
        )
        assert check_shell_injection(wf) == []


class TestS002HardcodedPaths:
    def test_hardcoded_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="run",
                    step_type=StepType.SHELL,
                    raw_params={"command": "cat /home/user/data.txt"},
                ),
            ],
        )
        findings = check_hardcoded_paths(wf)
        assert len(findings) == 1

    def test_relative_path_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="run",
                    step_type=StepType.SHELL,
                    raw_params={"command": "cat data.txt"},
                ),
            ],
        )
        assert check_hardcoded_paths(wf) == []


class TestS003InputValidation:
    def test_no_type_flagged(self) -> None:
        wf = _wf(
            inputs={"query": {"required": True}},
            steps=[ParsedStep(id="s1", step_type=StepType.LLM)],
        )
        findings = check_input_validation(wf)
        assert len(findings) == 1

    def test_with_type_clean(self) -> None:
        wf = _wf(
            inputs={"query": {"required": True, "type": "string"}},
            steps=[ParsedStep(id="s1", step_type=StepType.LLM)],
        )
        assert check_input_validation(wf) == []

    def test_optional_not_flagged(self) -> None:
        wf = _wf(
            inputs={"query": {"required": False}},
            steps=[ParsedStep(id="s1", step_type=StepType.LLM)],
        )
        assert check_input_validation(wf) == []


class TestS004McpNoServer:
    def test_no_server_flagged(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="mcp",
                    step_type=StepType.MCP_TOOL,
                    raw_params={"tool": "search"},
                ),
            ],
        )
        findings = check_mcp_no_server(wf)
        assert len(findings) == 1

    def test_with_server_clean(self) -> None:
        wf = _wf(
            steps=[
                ParsedStep(
                    id="mcp",
                    step_type=StepType.MCP_TOOL,
                    raw_params={"server": "github", "tool": "search"},
                ),
            ],
        )
        assert check_mcp_no_server(wf) == []
