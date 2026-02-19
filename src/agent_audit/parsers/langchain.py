"""Parser for LangChain/LangGraph workflow YAML files."""

from __future__ import annotations

from typing import Any

from agent_audit.models import ParsedStep, ParsedWorkflow, StepType, WorkflowFormat


def _node_to_step(node: dict[str, Any], index: int) -> ParsedStep:
    """Convert a LangGraph node definition to a ParsedStep."""
    step_id = str(node.get("id", node.get("name", f"node_{index}")))

    # Detect step type from node properties.
    node_type = str(node.get("type", "")).lower()
    if node_type in ("tool", "function"):
        step_type = StepType.SHELL
    elif node_type in ("branch", "conditional"):
        step_type = StepType.BRANCH
    elif node_type == "parallel":
        step_type = StepType.PARALLEL
    else:
        step_type = StepType.LLM

    return ParsedStep(
        id=step_id,
        step_type=step_type,
        provider=node.get("provider"),
        model=node.get("model"),
        role=node.get("role"),
        estimated_tokens=node.get("max_tokens"),
        raw_params=node,
    )


def parse_langchain(raw: dict[str, Any], *, source_path: str | None = None) -> ParsedWorkflow:
    """Parse a LangChain/LangGraph workflow dict into a ParsedWorkflow."""
    name = str(raw.get("name", raw.get("graph", "unnamed-graph")))

    steps: list[ParsedStep] = []

    # Parse nodes.
    for i, node in enumerate(raw.get("nodes", [])):
        if isinstance(node, dict):
            steps.append(_node_to_step(node, i))

    # Wire up dependencies from edges.
    edges = raw.get("edges", [])
    step_ids = {s.id for s in steps}
    for edge in edges:
        if isinstance(edge, dict):
            source = str(edge.get("source", edge.get("from", "")))
            target = str(edge.get("target", edge.get("to", "")))
            if source in step_ids and target in step_ids:
                for s in steps:
                    if s.id == target and source not in s.depends_on:
                        s.depends_on.append(source)

    return ParsedWorkflow(
        name=name,
        format=WorkflowFormat.LANGCHAIN,
        token_budget=raw.get("token_budget"),
        steps=steps,
        inputs=raw.get("inputs", {}),
        metadata=raw.get("metadata", {}),
        source_path=source_path,
    )
