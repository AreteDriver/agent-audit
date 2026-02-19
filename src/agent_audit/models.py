"""Pydantic v2 models for agent-audit."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkflowFormat(StrEnum):
    """Supported workflow config formats."""

    GORGON = "gorgon"
    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    GENERIC = "generic"


class StepType(StrEnum):
    """Normalized step types across all formats."""

    LLM = "llm"
    SHELL = "shell"
    PARALLEL = "parallel"
    CHECKPOINT = "checkpoint"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"
    MAP_REDUCE = "map_reduce"
    BRANCH = "branch"
    LOOP = "loop"
    MCP_TOOL = "mcp_tool"


class Severity(StrEnum):
    """Lint finding severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(StrEnum):
    """Lint rule categories."""

    BUDGET = "budget"
    RESILIENCE = "resilience"
    EFFICIENCY = "efficiency"
    SECURITY = "security"


# ---------------------------------------------------------------------------
# Parsed workflow models
# ---------------------------------------------------------------------------


class ParsedStep(BaseModel):
    """Normalized step from any workflow format."""

    id: str
    step_type: StepType
    provider: str | None = None
    model: str | None = None
    role: str | None = None
    estimated_tokens: int | None = None
    on_failure: str | None = None
    max_retries: int = 0
    timeout_seconds: int | None = None
    has_condition: bool = False
    has_fallback: bool = False
    depends_on: list[str] = Field(default_factory=list)
    nested_steps: list[ParsedStep] = Field(default_factory=list)
    raw_params: dict[str, Any] = Field(default_factory=dict)


class ParsedWorkflow(BaseModel):
    """Normalized workflow from any format."""

    name: str
    version: str = "1.0"
    description: str = ""
    format: WorkflowFormat
    token_budget: int | None = None
    timeout_seconds: int | None = None
    steps: list[ParsedStep]
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_path: str | None = None


# ---------------------------------------------------------------------------
# Estimation models
# ---------------------------------------------------------------------------


class StepEstimate(BaseModel):
    """Token and cost estimate for a single step."""

    step_id: str
    step_type: StepType
    provider: str
    model: str
    role: str | None = None
    estimated_tokens: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    source: Literal["declared", "archetype", "default"]


class WorkflowEstimate(BaseModel):
    """Full workflow cost estimate."""

    workflow_name: str
    total_tokens: int
    total_cost_usd: float
    budget_declared: int | None = None
    budget_utilization: float | None = None
    steps: list[StepEstimate]
    provider: str
    model: str


# ---------------------------------------------------------------------------
# Lint models
# ---------------------------------------------------------------------------


class LintFinding(BaseModel):
    """A single lint finding."""

    rule_id: str
    category: RuleCategory
    severity: Severity
    message: str
    step_id: str | None = None
    suggestion: str | None = None


class LintReport(BaseModel):
    """Full lint report with score."""

    workflow_name: str
    score: int = Field(ge=0, le=100)
    findings: list[LintFinding]
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0


# ---------------------------------------------------------------------------
# Pricing models
# ---------------------------------------------------------------------------


class ModelPricing(BaseModel):
    """Pricing for a single model."""

    name: str
    provider: str
    input_price_per_1k: float
    output_price_per_1k: float
    context_window: int = 0
    notes: str = ""


class ProviderConfig(BaseModel):
    """A provider's models and default selection."""

    name: str
    models: dict[str, ModelPricing]
    default_model: str


# ---------------------------------------------------------------------------
# Compare models
# ---------------------------------------------------------------------------


class CompareResult(BaseModel):
    """Multi-provider cost comparison."""

    workflow_name: str
    estimates: list[WorkflowEstimate]
    cheapest: str
    most_expensive: str
    savings_pct: float
