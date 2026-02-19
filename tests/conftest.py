"""Shared test fixtures for agent-audit."""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Sample Gorgon workflow YAML
# ---------------------------------------------------------------------------

GORGON_FEATURE_BUILD = """\
name: Feature Build
version: "1.0"
description: Multi-agent feature build
token_budget: 150000
timeout_seconds: 3600

inputs:
  feature_request:
    type: string
    required: true

outputs:
  - plan
  - code
  - review

steps:
  - id: plan
    type: claude_code
    params:
      role: planner
      prompt: "Plan the feature: ${feature_request}"
      estimated_tokens: 5000
    on_failure: abort
    outputs:
      - plan

  - id: build
    type: claude_code
    params:
      role: builder
      prompt: "Build: ${plan}"
      estimated_tokens: 20000
    on_failure: retry
    max_retries: 2
    outputs:
      - code

  - id: checkpoint_build
    type: checkpoint
    params:
      message: "Build complete"

  - id: test
    type: claude_code
    params:
      role: tester
      prompt: "Test: ${code}"
      estimated_tokens: 10000
    on_failure: retry
    max_retries: 2

  - id: run_tests
    type: shell
    params:
      command: "pytest"
    on_failure: abort
    timeout_seconds: 300

  - id: review
    type: claude_code
    params:
      role: reviewer
      prompt: "Review: ${code}"
      estimated_tokens: 5000
    condition:
      field: test_results
      operator: contains
      value: "passed"
    on_failure: skip

metadata:
  author: gorgon
  category: development
"""

GORGON_PARALLEL = """\
name: Parallel Review
version: "1.0"
token_budget: 50000

steps:
  - id: read_code
    type: shell
    params:
      command: "cat src/*.py"
    timeout_seconds: 60

  - id: security_review
    type: claude_code
    params:
      role: reviewer
      prompt: "Security review"
      estimated_tokens: 8000

  - id: performance_review
    type: claude_code
    params:
      role: reviewer
      prompt: "Performance review"
      estimated_tokens: 8000

  - id: summarize
    type: claude_code
    params:
      role: reviewer
      prompt: "Summarize"
      estimated_tokens: 3000
"""

GORGON_NO_BUDGET = """\
name: No Budget Workflow
steps:
  - id: plan
    type: claude_code
    params:
      role: planner
      prompt: "Plan"
  - id: build
    type: claude_code
    params:
      role: builder
      prompt: "Build"
"""

GORGON_SHELL_NO_TIMEOUT = """\
name: Shell Workflow
token_budget: 50000
steps:
  - id: run
    type: shell
    params:
      command: "make build"
  - id: deploy
    type: shell
    params:
      command: "cd ${path} && ./deploy.sh"
"""

CREWAI_SAMPLE = """\
name: Research Crew
agents:
  - role: researcher
    goal: Find information
    model: gpt-4o
  - role: writer
    goal: Write report
    model: gpt-4o
tasks:
  - description: Research topic
    agent: researcher
  - description: Write summary
    agent: writer
"""

LANGCHAIN_SAMPLE = """\
name: Analysis Graph
nodes:
  - id: fetch
    type: retriever
  - id: analyze
    type: llm
    model: gpt-4o
edges:
  - source: fetch
    target: analyze
"""

GENERIC_SAMPLE = """\
name: Simple Pipeline
steps:
  - id: generate
    prompt: "Generate content"
    model: gpt-4o
  - id: review
    prompt: "Review content"
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gorgon_workflow_path(tmp_path: Path) -> Path:
    """Write Gorgon feature-build workflow to a temp file."""
    p = tmp_path / "feature-build.yaml"
    p.write_text(GORGON_FEATURE_BUILD, encoding="utf-8")
    return p


@pytest.fixture
def gorgon_parallel_path(tmp_path: Path) -> Path:
    p = tmp_path / "parallel-review.yaml"
    p.write_text(GORGON_PARALLEL, encoding="utf-8")
    return p


@pytest.fixture
def gorgon_no_budget_path(tmp_path: Path) -> Path:
    p = tmp_path / "no-budget.yaml"
    p.write_text(GORGON_NO_BUDGET, encoding="utf-8")
    return p


@pytest.fixture
def gorgon_shell_path(tmp_path: Path) -> Path:
    p = tmp_path / "shell.yaml"
    p.write_text(GORGON_SHELL_NO_TIMEOUT, encoding="utf-8")
    return p


@pytest.fixture
def crewai_path(tmp_path: Path) -> Path:
    p = tmp_path / "crewai.yaml"
    p.write_text(CREWAI_SAMPLE, encoding="utf-8")
    return p


@pytest.fixture
def langchain_path(tmp_path: Path) -> Path:
    p = tmp_path / "langchain.yaml"
    p.write_text(LANGCHAIN_SAMPLE, encoding="utf-8")
    return p


@pytest.fixture
def generic_path(tmp_path: Path) -> Path:
    p = tmp_path / "generic.yaml"
    p.write_text(GENERIC_SAMPLE, encoding="utf-8")
    return p
