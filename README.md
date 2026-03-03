# agent-lint

[![CI](https://github.com/AreteDriver/agent-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/AreteDriver/agent-lint/actions/workflows/ci.yml)
[![CodeQL](https://github.com/AreteDriver/agent-lint/actions/workflows/codeql.yml/badge.svg)](https://github.com/AreteDriver/agent-lint/actions/workflows/codeql.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Catch expensive agent pipelines before they run.**

`agent-lint` is the eslint of agent workflows. It reads your YAML configs, flags structural problems, and tells you what a run will cost — before you press enter.

```
$ agent-lint lint workflow.yaml

  3 steps validated
  [warn] step 2: model=claude-opus-4-6 — consider claude-sonnet-4-6 (~$0.18 -> ~$0.02 per run)
  [warn] step 3: no max_tokens set — cost unbounded
  [fail] step 1: missing fallback handler — silent failure risk

  Score: 62/100

$ agent-lint estimate workflow.yaml

  Step 1  researcher    claude-sonnet-4-6    ~4,200 tokens    $0.02
  Step 2  writer        claude-opus-4-6      ~8,800 tokens    $0.18
  Step 3  reviewer      claude-sonnet-4-6    ~3,100 tokens    $0.01
  ──────────────────────────────────────────────────────────────────
  Total                                     ~16,100 tokens    $0.21
  Monthly (3x/day)                                           ~$19
```

No proxies. No SDK integration. Just point it at your workflow file.

## Install

```bash
pip install agentlinter
```

## Why

Every agent framework lets you *run* workflows. None of them tell you what it will cost before you do. You find out three days later when the invoice arrives.

`agent-lint` catches the problems that don't show up in testing:

- The step using Opus when Sonnet would do
- The loop with no max_tokens that could run up a $200 bill
- The missing error handler that silently retries (and silently bills)
- The hardcoded path that works on your machine and nowhere else

## Usage

```bash
# Estimate costs for a workflow
agent-lint estimate workflow.yaml
agent-lint estimate workflow.yaml --provider openai
agent-lint estimate workflow.yaml --json

# Lint for anti-patterns
agent-lint lint workflow.yaml
agent-lint lint workflow.yaml --fail-under 80   # CI gate

# Compare providers side-by-side (Pro)
agent-lint compare workflow.yaml

# Check license status
agent-lint status
```

## Supported Formats

| Format | Detection |
|--------|-----------|
| Gorgon/Forge | `steps[].type` matches known step types |
| CrewAI | `agents` + `tasks` top-level keys |
| LangChain/LangGraph | `nodes` or `edges` structure |
| Generic | Any YAML with step-like structures |

## Lint Rules

17 rules across 4 categories:

| Category | What it catches | IDs |
|----------|----------------|-----|
| **Budget** | Missing budgets, unbounded costs, over-budget steps | B001-B004 |
| **Resilience** | Missing error handlers, no retries, no timeouts | R001-R005 |
| **Efficiency** | Missed parallelization, redundant steps | E001-E004 |
| **Security** | Prompt injection risk, hardcoded paths/secrets | S001-S004 |

## How It Compares

| | Pre-run cost estimate | Workflow linting | No proxy required | CLI-native |
|---|:---:|:---:|:---:|:---:|
| **agent-lint** | Yes | Yes | Yes | Yes |
| Langfuse | No (post-run) | No | No (SDK required) | No |
| Datadog LLM Observability | No (post-run) | No | No (agent required) | No |
| Manual review | No | No | Yes | -- |

## CI Integration

```yaml
# .github/workflows/agent-lint.yml
- name: Lint agent workflows
  run: agent-lint lint workflows/ --fail-under 80
```

Exits non-zero when the health score drops below your threshold.

## Free vs Pro

| Feature | Free | Pro |
|---------|:---:|:---:|
| Cost estimation | Yes | Yes |
| Lint (17 rules) | Yes | Yes |
| JSON output | Yes | Yes |
| Multi-provider comparison | -- | Yes |
| Markdown export | -- | Yes |
| Custom pricing tables | -- | Yes |

## License

MIT
