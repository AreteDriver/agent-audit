"""Parser for Gorgon/Forge workflow YAML files."""

from __future__ import annotations

from typing import Any

from agent_audit.config import LLM_STEP_TYPES, STEP_TYPE_PROVIDER_MAP
from agent_audit.models import ParsedStep, ParsedWorkflow, StepType, WorkflowFormat

# Map Gorgon step type strings to normalized StepType.
_TYPE_MAP: dict[str, StepType] = {
    "claude_code": StepType.LLM,
    "openai": StepType.LLM,
    "shell": StepType.SHELL,
    "parallel": StepType.PARALLEL,
    "checkpoint": StepType.CHECKPOINT,
    "fan_out": StepType.FAN_OUT,
    "fan_in": StepType.FAN_IN,
    "map_reduce": StepType.MAP_REDUCE,
    "branch": StepType.BRANCH,
    "loop": StepType.LOOP,
    "mcp_tool": StepType.MCP_TOOL,
}


def _parse_step(raw: dict[str, Any]) -> ParsedStep:
    """Parse a single Gorgon step dict into a ParsedStep."""
    step_id = str(raw.get("id", "unknown"))
    raw_type = str(raw.get("type", "shell"))
    step_type = _TYPE_MAP.get(raw_type, StepType.SHELL)

    params = raw.get("params", {}) or {}

    # Provider detection.
    provider: str | None = None
    model: str | None = None
    if raw_type in LLM_STEP_TYPES:
        provider = STEP_TYPE_PROVIDER_MAP.get(raw_type)
        model = params.get("model")

    role = params.get("role")
    estimated_tokens = params.get("estimated_tokens")

    # Dependencies.
    depends_on_raw = raw.get("depends_on", [])
    if isinstance(depends_on_raw, str):
        depends_on = [depends_on_raw]
    elif isinstance(depends_on_raw, list):
        depends_on = [str(d) for d in depends_on_raw]
    else:
        depends_on = []

    # Nested steps (for parallel, fan_out, map_reduce, loop).
    nested_steps: list[ParsedStep] = []
    for key in ("steps", "step_template", "map_step", "reduce_step"):
        nested_raw = params.get(key) or raw.get(key)
        if isinstance(nested_raw, list):
            nested_steps.extend(_parse_step(s) for s in nested_raw if isinstance(s, dict))
        elif isinstance(nested_raw, dict):
            nested_steps.append(_parse_step(nested_raw))

    return ParsedStep(
        id=step_id,
        step_type=step_type,
        provider=provider,
        model=model,
        role=role,
        estimated_tokens=estimated_tokens,
        on_failure=raw.get("on_failure"),
        max_retries=int(raw.get("max_retries", 0)),
        timeout_seconds=raw.get("timeout_seconds"),
        has_condition="condition" in raw,
        has_fallback="fallback" in raw,
        depends_on=depends_on,
        nested_steps=nested_steps,
        raw_params=params,
    )


def parse_gorgon(raw: dict[str, Any], *, source_path: str | None = None) -> ParsedWorkflow:
    """Parse a Gorgon/Forge workflow dict into a ParsedWorkflow."""
    name = str(raw.get("name", "unnamed"))
    version = str(raw.get("version", "1.0"))
    description = str(raw.get("description", ""))

    steps_raw = raw.get("steps", [])
    steps = [_parse_step(s) for s in steps_raw if isinstance(s, dict)]

    outputs_raw = raw.get("outputs", [])
    outputs = [str(o) for o in outputs_raw] if isinstance(outputs_raw, list) else []

    return ParsedWorkflow(
        name=name,
        version=version,
        description=description,
        format=WorkflowFormat.GORGON,
        token_budget=raw.get("token_budget"),
        timeout_seconds=raw.get("timeout_seconds"),
        steps=steps,
        inputs=raw.get("inputs", {}),
        outputs=outputs,
        metadata=raw.get("metadata", {}),
        source_path=source_path,
    )
