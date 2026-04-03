# CLAUDE.md — agent-lint

## Project Overview
CLI tool that analyzes agent workflow YAML configs for cost estimation, anti-pattern detection (linting), and multi-provider comparison. Supports Gorgon/Forge, CrewAI, LangChain/LangGraph, and generic YAML formats.

## Quick Start
```bash
cd ./
source .venv/bin/activate
pip install -e ".[dev]"
```

## Common Commands
```bash
# Testing
pytest                                    # Run all 281 tests (coverage gate: 90%)
pytest tests/test_cli.py -v               # Single module
pytest -k "test_estimate" -v              # Filter by name

# Linting & Formatting
ruff check src/ tests/                    # Lint
ruff format src/ tests/                   # Format
ruff check src/ tests/ && ruff format src/ tests/  # Both (always run both)

# Type Checking
mypy src/                                 # Strict mode enabled

# Build & Install
pip install -e ".[dev]"                   # Editable install with dev deps
pip install -e ".[dev,server]"            # Include httpx for license server

# CLI Usage
agent-lint estimate workflow.yaml         # Cost estimate
agent-lint lint workflow.yaml             # Lint for anti-patterns
agent-lint compare workflow.yaml          # Multi-provider comparison (Pro)
agent-lint status                         # License tier
agent-lint stats                          # Usage telemetry
```

## Architecture
- **src layout**: `src/agent_lint/` with 16 modules across 4 packages
- **Entry point**: `agent-lint = "agent_lint.cli:app"` (Typer)
- **Models**: Pydantic v2 (`models.py`)
- **Parsers**: Strategy pattern — `detect_format()` dispatches to format-specific parser
- **Estimator**: 3-tier token resolution (declared → archetype → default), bundled pricing YAML
- **Linter**: `@lint_rule` decorator registry, 17 rules across 4 categories
- **Licensing**: HMAC-checksum keys, prefix `ALNT`, salt `agent-lint-v1`

## CLI Reference
```bash
agent-lint estimate workflow.yaml                    # Cost estimate (table)
agent-lint estimate workflow.yaml --json             # JSON output
agent-lint estimate workflow.yaml --format markdown  # Markdown output (Pro)
agent-lint estimate workflow.yaml --provider ollama  # Override provider
agent-lint lint workflow.yaml                        # Lint for anti-patterns
agent-lint lint workflow.yaml --category budget      # Filter by category
agent-lint lint workflow.yaml --fail-under 80        # CI mode (exit 1 if below)
agent-lint compare workflow.yaml                     # Multi-provider comparison (Pro)
agent-lint status                                    # Show license tier
agent-lint stats                                     # Local usage telemetry
agent-lint stats --json                              # Telemetry as JSON
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
| stats | Yes | Yes |
| compare | No | Yes |
| markdown_export | No | Yes |
| custom_pricing | No | Yes |

## Testing
- 296 tests, pytest, 98% coverage (fail_under=90)
- `tests/conftest.py` has sample workflow YAML fixtures (Gorgon, CrewAI, LangChain, Generic)
- `tests/test_coverage_push_90.py` — targeted coverage for crewai, langchain, generic parsers + CLI branches
- Coverage gate enforced via `addopts` in pyproject.toml (pytest-cov)

## CI/CD
- **CI**: lint (ruff check + format) + test matrix on push/PR (`ci.yml`)
- **CodeQL**: security scanning (`codeql.yml`)
- **Secret Scan**: gitleaks v8.24.3 on push/PR to main (`secret-scan.yml`)
- **Security**: pip-audit on push/PR + weekly Monday 6am UTC (`security.yml`)
- **Release**: tag-triggered `v*` — pytest gate → build → GitHub Release (softprops/action-gh-release) → PyPI OIDC publish (`release.yml`)
- **Gitleaks allowlist**: `.gitleaks.toml` — `agent-lint-v1` salt + `tests/` path
- **PyPI**: OIDC Trusted Publisher, `environment: pypi`

## Coding Standards
- Python 3.11+, `from __future__ import annotations` in every file
- Type hints on all public functions (mypy strict mode enforced)
- Pydantic v2 for models — use `model_validator`, not legacy validators
- `@lint_rule` decorator for new rules — auto-registered, no manual wiring
- Strategy pattern for parsers — new formats implement parser interface + `detect_format()` clause
- Ruff lint + format (B008 suppressed for cli.py — Typer `Option()` pattern)
- Dependencies: typer, rich, pydantic, pyyaml (httpx optional for server validation)
- Three-name scheme: PyPI=`agentlinter`, import=`agent_lint`, CLI=`agent-lint`
- Local directory: project root

## Git Conventions
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Run `ruff check src/ tests/ && ruff format src/ tests/` before committing
- Run `pytest` before pushing (coverage gate: 90%)
- Release: push `v*` tag → CI runs tests → builds → GitHub Release → PyPI OIDC publish

## Domain Context
agent-lint targets AI/ML engineers building multi-agent workflows. The core value prop is catching cost and reliability issues *before* running expensive agent pipelines. Supported frameworks (Gorgon/Forge, CrewAI, LangChain/LangGraph) each have different YAML schemas — the parser strategy pattern normalizes them into a common `WorkflowModel`. Pricing data is bundled as YAML in `src/agent_lint/data/` and covers Anthropic, OpenAI, and Ollama (local/free) providers.

## Telemetry
- Opt-in via `AGENT_LINT_TELEMETRY=1` env var
- SQLite WAL store at `~/.agent-lint/telemetry.db` (override with `AGENT_LINT_DIR`)
- `track_command(name)` — records CLI invocations (no-op when disabled)
- `track_pro_gate(feature)` — records free-tier Pro feature attempts
- `stats` command shows usage tables (Rich) or `--json` output
- Module-level singleton with `reset_telemetry_store()` for test isolation
