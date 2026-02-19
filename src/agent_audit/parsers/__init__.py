"""Workflow format detection and parsing dispatch."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from agent_audit.exceptions import ParseError
from agent_audit.models import ParsedWorkflow, WorkflowFormat

logger = logging.getLogger(__name__)

# Gorgon step types that signal the format.
_GORGON_STEP_TYPES = {
    "claude_code",
    "openai",
    "shell",
    "parallel",
    "checkpoint",
    "fan_out",
    "fan_in",
    "map_reduce",
    "branch",
    "loop",
    "mcp_tool",
}


def detect_format(raw: dict[str, Any]) -> WorkflowFormat:
    """Detect workflow format from YAML structure."""
    # CrewAI: has both 'agents' and 'tasks' top-level keys.
    if "agents" in raw and "tasks" in raw:
        return WorkflowFormat.CREWAI

    # LangChain/LangGraph: has 'nodes' or 'edges', or langgraph in metadata.
    if "nodes" in raw or "edges" in raw:
        return WorkflowFormat.LANGCHAIN
    meta = raw.get("metadata", {})
    if isinstance(meta, dict) and "langgraph" in str(meta).lower():
        return WorkflowFormat.LANGCHAIN

    # Gorgon: has 'steps' list where items have 'type' in known set.
    steps = raw.get("steps", [])
    if isinstance(steps, list) and steps:
        for step in steps:
            if isinstance(step, dict) and step.get("type") in _GORGON_STEP_TYPES:
                return WorkflowFormat.GORGON

    return WorkflowFormat.GENERIC


def load_yaml(path: Path) -> dict[str, Any]:
    """Load and validate a YAML file."""
    if not path.is_file():
        raise ParseError(f"File not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Failed to read {path}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ParseError(f"Expected YAML mapping at top level in {path}")

    return raw


def parse_workflow(path: Path) -> ParsedWorkflow:
    """Load a workflow YAML and parse it into a normalized model."""
    raw = load_yaml(path)
    fmt = detect_format(raw)

    if fmt == WorkflowFormat.GORGON:
        from agent_audit.parsers.gorgon import parse_gorgon

        return parse_gorgon(raw, source_path=str(path))

    if fmt == WorkflowFormat.CREWAI:
        from agent_audit.parsers.crewai import parse_crewai

        return parse_crewai(raw, source_path=str(path))

    if fmt == WorkflowFormat.LANGCHAIN:
        from agent_audit.parsers.langchain import parse_langchain

        return parse_langchain(raw, source_path=str(path))

    from agent_audit.parsers.generic import parse_generic

    return parse_generic(raw, source_path=str(path))
