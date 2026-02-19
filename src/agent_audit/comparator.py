"""Multi-provider cost comparison engine."""

from __future__ import annotations

from agent_audit.estimator import estimate_workflow
from agent_audit.models import CompareResult, ParsedWorkflow, WorkflowEstimate
from agent_audit.pricing import list_providers, load_providers


def compare_providers(
    workflow: ParsedWorkflow,
    providers: list[str] | None = None,
) -> CompareResult:
    """Estimate workflow cost across multiple providers and compare."""
    all_providers = load_providers()

    if providers is None:
        providers = list_providers(providers=all_providers)

    estimates: list[WorkflowEstimate] = []
    for provider in providers:
        est = estimate_workflow(workflow, provider=provider)
        estimates.append(est)

    if not estimates:
        return CompareResult(
            workflow_name=workflow.name,
            estimates=[],
            cheapest="",
            most_expensive="",
            savings_pct=0.0,
        )

    cheapest = min(estimates, key=lambda e: e.total_cost_usd)
    most_expensive = max(estimates, key=lambda e: e.total_cost_usd)

    savings = 0.0
    if most_expensive.total_cost_usd > 0:
        savings = round((1 - cheapest.total_cost_usd / most_expensive.total_cost_usd) * 100, 1)

    return CompareResult(
        workflow_name=workflow.name,
        estimates=estimates,
        cheapest=cheapest.provider,
        most_expensive=most_expensive.provider,
        savings_pct=savings,
    )
