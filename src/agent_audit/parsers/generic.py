"""Generic fallback parser for unrecognized workflow formats."""

from __future__ import annotations

from typing import Any

from agent_audit.models import ParsedStep, ParsedWorkflow, StepType, WorkflowFormat


def _guess_step_type(config: dict[str, Any]) -> StepType:
    """Best-effort step type detection from arbitrary dict."""
    if "command" in config or "cmd" in config:
        return StepType.SHELL
    if "prompt" in config or "model" in config or "llm" in config:
        return StepType.LLM
    if "steps" in config and isinstance(config["steps"], list):
        return StepType.PARALLEL
    return StepType.LLM


def _parse_generic_step(step_id: str, config: dict[str, Any]) -> ParsedStep:
    """Parse a step from generic YAML."""
    step_type = _guess_step_type(config)

    return ParsedStep(
        id=step_id,
        step_type=step_type,
        provider=config.get("provider"),
        model=config.get("model"),
        role=config.get("role"),
        estimated_tokens=config.get("estimated_tokens") or config.get("max_tokens"),
        on_failure=config.get("on_failure") or config.get("on_error"),
        max_retries=int(config.get("max_retries", 0)),
        timeout_seconds=config.get("timeout") or config.get("timeout_seconds"),
        raw_params=config,
    )


def parse_generic(raw: dict[str, Any], *, source_path: str | None = None) -> ParsedWorkflow:
    """Parse a generic workflow YAML into a ParsedWorkflow."""
    name = str(raw.get("name", raw.get("workflow", "unnamed")))

    # Try 'steps' as a list of dicts with 'id' or 'name' keys.
    steps: list[ParsedStep] = []
    steps_raw = raw.get("steps", [])
    if isinstance(steps_raw, list):
        for i, item in enumerate(steps_raw):
            if isinstance(item, dict):
                step_id = str(item.get("id", item.get("name", f"step_{i}")))
                steps.append(_parse_generic_step(step_id, item))
    elif isinstance(steps_raw, dict):
        # Steps as a name→config mapping.
        for step_id, config in steps_raw.items():
            if isinstance(config, dict):
                steps.append(_parse_generic_step(str(step_id), config))

    # If no 'steps' key, look for 'agents' or 'tasks' as flat list.
    if not steps:
        for key in ("agents", "tasks", "pipeline"):
            items = raw.get(key, [])
            if isinstance(items, list):
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        step_id = str(item.get("id", item.get("name", f"{key}_{i}")))
                        steps.append(_parse_generic_step(step_id, item))
                break

    return ParsedWorkflow(
        name=name,
        format=WorkflowFormat.GENERIC,
        token_budget=raw.get("token_budget") or raw.get("budget"),
        steps=steps,
        inputs=raw.get("inputs", {}),
        outputs=raw.get("outputs", []) if isinstance(raw.get("outputs"), list) else [],
        metadata=raw.get("metadata", {}),
        source_path=source_path,
    )
