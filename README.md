# agent-lint

**CLI tool for cost estimation and anti-pattern detection in agent workflow YAML configs.**
Catch expensive, fragile, or ungoverned agent workflows before they hit production.

[![PyPI](https://img.shields.io/pypi/v/agentlinter.svg)](https://pypi.org/project/agentlinter/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/AreteDriver/agent-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/AreteDriver/agent-lint/actions)

---

## The Problem

Agent workflows fail in predictable ways: unbounded loops, no retry limits, missing cost guards, parallel branches with no coordination. Most teams find these problems in production — after a $400 API bill or a stuck workflow that ran for six hours.

`agent-lint` finds them at config time.

---

## Install

```bash
pip install agentlinter
```

---

## Usage

```bash
# Lint a single workflow config
agent-lint lint workflow.yaml

# Lint all workflows in a directory, fail CI if score < 80
agent-lint lint workflows/ --fail-under 80

# Estimate token/cost exposure for a workflow
agent-lint estimate workflow.yaml --provider anthropic

# Generate a full audit report
agent-lint lint workflows/ --format markdown
```

---

## What It Detects

**Anti-patterns:**
- Unbounded retry loops (no max_retries or timeout)
- Missing cost guards on high-token operations
- Parallel agent branches with no merge strategy
- Hard-coded API keys in config (security)
- Missing checkpointing on long-running workflows
- Agents with no defined output schema

**Cost estimation:**
- Token budget projection per workflow step
- Worst-case / expected-case / best-case cost ranges
- Model-aware pricing (Claude, GPT-4, Gemini)

**Scoring:**
- 0-100 score per workflow
- Error (-15 pts), warning (-5 pts), info (-1 pt)
- CI integration: `--fail-under` threshold

---

## CI Integration

```yaml
# .github/workflows/agent-lint.yml
- name: Lint agent workflows
  run: agent-lint lint workflows/ --fail-under 80
```

Treat your agent configs like production code. Gate them the same way.

---

## Why Static Analysis

No LLM dependency. No API calls. No variance between runs.
Agent configs are deterministic artifacts — they should be audited deterministically.

---

## Status

- [x] Anti-pattern detection (17 rules)
- [x] Cost estimation (Claude, GPT-4)
- [x] CI integration with threshold gating
- [x] Markdown audit reports
- [ ] Gemini pricing model
- [ ] VS Code extension
- [ ] Auto-fix suggestions

---

## Free vs Pro

| Feature | Free | Pro ($8/mo) |
|---------|:----:|:-----------:|
| `lint` — 17 anti-pattern rules | Yes | Yes |
| `estimate` — token/cost estimation | Yes | Yes |
| `status` — license and system info | Yes | Yes |
| `compare` — multi-provider cost comparison | - | Yes |
| Markdown export | - | Yes |
| Custom pricing models | - | Yes |
| Custom lint rules | - | Yes |
| Historical tracking | - | Yes |

**Get Pro:** [Monthly ($8/mo)](https://buy.stripe.com/dRm9AT3WPbp95habIzgrS02) | [Yearly ($69/yr)](https://buy.stripe.com/6oU00j0KDgJt4d6aEvgrS03)

**Activate:**
```bash
export AGENT_LINT_LICENSE=ALNT-XXXX-XXXX-XXXX
```

---

*Part of the [AreteDriver](https://github.com/AreteDriver) AI tooling ecosystem.*
