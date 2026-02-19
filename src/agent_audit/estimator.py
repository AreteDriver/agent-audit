"""Token estimation engine."""

from __future__ import annotations

from agent_audit.config import (
    INPUT_OUTPUT_RATIO,
    ROLE_TOKEN_DEFAULTS,
    STEP_TYPE_TOKEN_DEFAULTS,
)
from agent_audit.models import (
    ParsedStep,
    ParsedWorkflow,
    StepEstimate,
    StepType,
    WorkflowEstimate,
)
from agent_audit.pricing import calculate_cost, get_model_pricing, load_providers


def _resolve_tokens(step: ParsedStep) -> tuple[int, str]:
    """Resolve token estimate for a step. Returns (tokens, source)."""
    # 1. Declared in YAML.
    if step.estimated_tokens is not None:
        return step.estimated_tokens, "declared"

    # 2. Archetype default by role.
    if step.role and step.role in ROLE_TOKEN_DEFAULTS:
        return ROLE_TOKEN_DEFAULTS[step.role], "archetype"

    # 3. Step type default.
    default = STEP_TYPE_TOKEN_DEFAULTS.get(step.step_type.value, 0)
    if step.step_type == StepType.LLM and default == 0:
        default = STEP_TYPE_TOKEN_DEFAULTS.get("llm", 8000)
    return default, "default"


def _split_tokens(total: int) -> tuple[int, int]:
    """Split total tokens into input/output based on ratio."""
    input_tokens = int(total * INPUT_OUTPUT_RATIO)
    output_tokens = total - input_tokens
    return input_tokens, output_tokens


def estimate_step(
    step: ParsedStep,
    provider: str,
    model: str,
) -> StepEstimate:
    """Estimate tokens and cost for a single step."""
    total_tokens, source = _resolve_tokens(step)

    # Container steps: sum nested step tokens.
    if step.nested_steps:
        nested_total = sum(_resolve_tokens(ns)[0] for ns in step.nested_steps)
        if nested_total > total_tokens:
            total_tokens = nested_total
            source = "declared" if step.estimated_tokens else "archetype"

    input_tokens, output_tokens = _split_tokens(total_tokens)

    # Non-LLM steps have zero cost regardless.
    if step.step_type != StepType.LLM:
        cost = 0.0
    else:
        pricing = get_model_pricing(provider, model)
        cost = calculate_cost(input_tokens, output_tokens, pricing)

    return StepEstimate(
        step_id=step.id,
        step_type=step.step_type,
        provider=provider,
        model=model,
        role=step.role,
        estimated_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        source=source,
    )


def estimate_workflow(
    workflow: ParsedWorkflow,
    provider: str | None = None,
    model: str | None = None,
) -> WorkflowEstimate:
    """Estimate total tokens and cost for a workflow."""
    providers = load_providers()

    # Track whether the user explicitly set the provider.
    explicit_provider = provider is not None

    # Determine default provider from first LLM step.
    if provider is None:
        for step in workflow.steps:
            if step.provider:
                provider = step.provider
                break
        if provider is None:
            provider = "anthropic"

    # Determine model.
    if model is None:
        config = providers.get(provider)
        model = config.default_model if config else "unknown"

    step_estimates: list[StepEstimate] = []
    for step in workflow.steps:
        # Explicit CLI provider overrides step-level providers.
        step_provider = provider if explicit_provider else step.provider or provider
        step_model = step.model or model
        step_estimates.append(estimate_step(step, step_provider, step_model))

    total_tokens = sum(e.estimated_tokens for e in step_estimates)
    total_cost = sum(e.cost_usd for e in step_estimates)

    budget_util: float | None = None
    if workflow.token_budget and workflow.token_budget > 0:
        budget_util = round((total_tokens / workflow.token_budget) * 100, 1)

    return WorkflowEstimate(
        workflow_name=workflow.name,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        budget_declared=workflow.token_budget,
        budget_utilization=budget_util,
        steps=step_estimates,
        provider=provider,
        model=model,
    )
