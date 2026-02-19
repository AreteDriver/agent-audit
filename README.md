# agent-audit

Estimate costs and lint agent workflow YAML files.

## Features

- **Cost Estimation** — Token usage and cost estimates per step with 3-tier fallback
- **Multi-Provider** — Claude (Sonnet/Opus/Haiku), OpenAI (GPT-4o/mini), Ollama (local/free)
- **Workflow Linter** — 17 rules across 4 categories (budget, resilience, efficiency, security)
- **Score** — 0-100 health score with configurable CI fail thresholds
- **Format Support** — Gorgon/Forge YAML natively, generic format detection

## Install

```bash
pip install agent-audit
```

## Usage

```bash
# Estimate costs
agent-audit estimate workflow.yaml
agent-audit estimate workflow.yaml --provider openai --json

# Lint for anti-patterns
agent-audit lint workflow.yaml
agent-audit lint workflow.yaml --fail-under 80  # CI gate

# Compare providers (Pro)
agent-audit compare workflow.yaml

# Check license
agent-audit status
```

## License

MIT
