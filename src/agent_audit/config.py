"""Configuration constants and defaults for agent-audit."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Token defaults by agent role (when estimated_tokens not declared).
# ---------------------------------------------------------------------------
ROLE_TOKEN_DEFAULTS: dict[str, int] = {
    "planner": 5000,
    "builder": 20000,
    "tester": 10000,
    "reviewer": 5000,
    "architect": 8000,
    "documenter": 6000,
    "analyst": 8000,
    "reporter": 4000,
    "visualizer": 5000,
    "security_auditor": 12000,
}

# Default tokens by step type when no role is specified.
STEP_TYPE_TOKEN_DEFAULTS: dict[str, int] = {
    "llm": 8000,
    "shell": 0,
    "checkpoint": 0,
    "mcp_tool": 0,
    "fan_in": 0,
    "branch": 0,
}

# Input/output token ratio (30% input, 70% output).
INPUT_OUTPUT_RATIO: float = 0.3

# ---------------------------------------------------------------------------
# Gorgon step type → provider mapping.
# ---------------------------------------------------------------------------
STEP_TYPE_PROVIDER_MAP: dict[str, str] = {
    "claude_code": "anthropic",
    "openai": "openai",
}

# ---------------------------------------------------------------------------
# Gorgon step types that are LLM-based (cost tokens).
# ---------------------------------------------------------------------------
LLM_STEP_TYPES: frozenset[str] = frozenset({"claude_code", "openai"})

# Non-LLM step types (zero token cost).
ZERO_COST_STEP_TYPES: frozenset[str] = frozenset(
    {
        "shell",
        "checkpoint",
        "mcp_tool",
        "fan_in",
        "branch",
    }
)

# Container step types (sum nested steps).
CONTAINER_STEP_TYPES: frozenset[str] = frozenset(
    {
        "parallel",
        "fan_out",
        "map_reduce",
        "loop",
    }
)

# ---------------------------------------------------------------------------
# Lint scoring weights.
# ---------------------------------------------------------------------------
SEVERITY_DEDUCTIONS: dict[str, int] = {
    "error": 10,
    "warning": 5,
    "info": 2,
}

# ---------------------------------------------------------------------------
# Paths.
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(__file__).parent / "data"
PROVIDERS_FILE: Path = DATA_DIR / "providers.yaml"
