"""Parser for CrewAI workflow YAML files."""

from __future__ import annotations

from typing import Any

from agent_audit.models import ParsedStep, ParsedWorkflow, StepType, WorkflowFormat


def _parse_agent(agent: dict[str, Any], index: int) -> ParsedStep:
    """Parse a CrewAI agent definition as a step."""
    step_id = str(agent.get("name", agent.get("role", f"agent_{index}")))
    role = str(agent.get("role", "")) or None

    return ParsedStep(
        id=step_id,
        step_type=StepType.LLM,
        provider=agent.get("llm_provider"),
        model=agent.get("llm") or agent.get("model"),
        role=role,
        estimated_tokens=agent.get("max_tokens"),
        raw_params=agent,
    )


def _parse_task(task: dict[str, Any], index: int) -> ParsedStep:
    """Parse a CrewAI task definition as a step."""
    step_id = str(task.get("name", task.get("description", f"task_{index}")[:40]))

    # Tasks may reference agents.
    depends_on: list[str] = []
    agent_ref = task.get("agent")
    if agent_ref:
        depends_on = [str(agent_ref)]

    return ParsedStep(
        id=step_id,
        step_type=StepType.LLM,
        role=task.get("role"),
        estimated_tokens=task.get("max_tokens"),
        depends_on=depends_on,
        raw_params=task,
    )


def parse_crewai(raw: dict[str, Any], *, source_path: str | None = None) -> ParsedWorkflow:
    """Parse a CrewAI workflow dict into a ParsedWorkflow."""
    name = str(raw.get("name", raw.get("crew", "unnamed-crew")))

    steps: list[ParsedStep] = []

    # Parse agents.
    for i, agent in enumerate(raw.get("agents", [])):
        if isinstance(agent, dict):
            steps.append(_parse_agent(agent, i))

    # Parse tasks.
    for i, task in enumerate(raw.get("tasks", [])):
        if isinstance(task, dict):
            steps.append(_parse_task(task, i))

    return ParsedWorkflow(
        name=name,
        format=WorkflowFormat.CREWAI,
        token_budget=raw.get("token_budget") or raw.get("max_tokens"),
        steps=steps,
        inputs=raw.get("inputs", {}),
        metadata=raw.get("metadata", {}),
        source_path=source_path,
    )
