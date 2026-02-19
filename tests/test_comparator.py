"""Tests for agent_audit.comparator."""

from __future__ import annotations

from pathlib import Path

from agent_audit.comparator import compare_providers
from agent_audit.parsers import parse_workflow


class TestCompareProviders:
    def test_compares_all_providers(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf)
        # Should have one estimate per bundled provider.
        assert len(result.estimates) >= 3
        assert result.cheapest
        assert result.most_expensive

    def test_ollama_cheapest(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf)
        assert result.cheapest == "ollama"

    def test_specific_providers(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf, providers=["anthropic", "openai"])
        assert len(result.estimates) == 2
        providers = {e.provider for e in result.estimates}
        assert providers == {"anthropic", "openai"}

    def test_savings_percentage(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf, providers=["anthropic", "ollama"])
        # Ollama is free, anthropic costs money → 100% savings.
        assert result.savings_pct == 100.0

    def test_single_provider(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf, providers=["anthropic"])
        assert len(result.estimates) == 1
        assert result.savings_pct == 0.0

    def test_workflow_name_propagated(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf)
        assert result.workflow_name == wf.name

    def test_empty_providers_list(self, gorgon_workflow_path: Path) -> None:
        wf = parse_workflow(gorgon_workflow_path)
        result = compare_providers(wf, providers=[])
        assert len(result.estimates) == 0
        assert result.cheapest == ""
        assert result.savings_pct == 0.0
