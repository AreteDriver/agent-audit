# CLAUDE.md — agent-audit

## Project Overview
CLI tool that analyzes agent workflow YAML configs for cost estimation, anti-pattern detection (linting), and multi-provider comparison. Supports Gorgon/Forge, CrewAI, LangChain/LangGraph, and generic YAML formats.

## Quick Start
```bash
cd /home/arete/projects/agent-audit
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/ && ruff format --check src/ tests/
```

## Architecture
- **src layout**: `src/agent_audit/` with 15 modules across 4 packages
- **Entry point**: `agent-audit = "agent_audit.cli:app"` (Typer)
- **Models**: Pydantic v2 (`models.py`)
- **Parsers**: Strategy pattern — `detect_format()` dispatches to format-specific parser
- **Estimator**: 3-tier token resolution (declared → archetype → default), bundled pricing YAML
- **Linter**: `@lint_rule` decorator registry, 17 rules across 4 categories
- **Licensing**: HMAC-checksum keys, prefix `AAUD`, salt `agent-audit-v1`

## Key Commands
```bash
agent-audit estimate workflow.yaml                    # Cost estimate (table)
agent-audit estimate workflow.yaml --json             # JSON output
agent-audit estimate workflow.yaml --format markdown  # Markdown output
agent-audit estimate workflow.yaml --provider ollama  # Override provider
agent-audit lint workflow.yaml                        # Lint for anti-patterns
agent-audit lint workflow.yaml --category budget      # Filter by category
agent-audit lint workflow.yaml --fail-under 80        # CI mode (exit 1 if below)
agent-audit compare workflow.yaml                     # Multi-provider comparison (Pro)
agent-audit status                                    # Show license tier
```

## Workflow Formats
| Format | Detection | Key Structure |
|--------|-----------|---------------|
| Gorgon | `steps[].type` in known set | claude_code, openai, shell, parallel, etc. |
| CrewAI | `agents` + `tasks` top-level | Agent definitions + task assignments |
| LangChain | `nodes` or `edges` | Graph-based node definitions |
| Generic | Fallback | Any YAML with step-like structures |

## Lint Rules (17 total)
| Category | Rules | IDs |
|----------|-------|-----|
| Budget | Missing budgets, over-budget | B001-B004 |
| Resilience | Missing handlers, no retries | R001-R005 |
| Efficiency | Parallelization, redundancy | E001-E004 |
| Security | Injection, hardcoded paths | S001-S004 |

## Token Estimation Strategy
Resolution order per step:
1. `estimated_tokens` from YAML → source: "declared"
2. `ROLE_TOKEN_DEFAULTS[role]` → source: "archetype"
3. `STEP_TYPE_TOKEN_DEFAULTS[step_type]` → source: "default"

## Monetization
| Feature | Free | Pro ($8/mo) |
|---------|------|-------------|
| estimate | Yes | Yes |
| lint | Yes | Yes |
| status | Yes | Yes |
| compare | No | Yes |
| markdown_export | No | Yes |
| custom_pricing | No | Yes |

## Testing
- 193 tests, pytest
- `tests/conftest.py` has sample workflow YAML fixtures
- All parsers tested via fixture files

## Conventions
- Python 3.11+, `from __future__ import annotations` everywhere
- Ruff lint + format (B008 suppressed for cli.py — Typer pattern)
- Dependencies: typer, rich, pydantic, pyyaml
