"""Tests for agent_audit.cli."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agent_audit import __version__
from agent_audit.cli import app

runner = CliRunner()


class TestVersion:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_short_version_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0


class TestNoArgs:
    def test_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code == 0


class TestEstimateCommand:
    def test_estimate_gorgon_workflow(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["estimate", str(gorgon_workflow_path)])
        assert result.exit_code == 0
        assert "Feature Build" in result.output
        assert "TOTAL" in result.output

    def test_estimate_json(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["estimate", str(gorgon_workflow_path), "--json"])
        assert result.exit_code == 0
        assert "total_tokens" in result.output

    def test_estimate_markdown(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["estimate", str(gorgon_workflow_path), "--format", "markdown"])
        assert result.exit_code == 0
        assert "| Step |" in result.output

    def test_estimate_with_provider(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["estimate", str(gorgon_workflow_path), "--provider", "ollama"])
        assert result.exit_code == 0
        assert "$0.0000" in result.output

    def test_estimate_missing_file(self) -> None:
        result = runner.invoke(app, ["estimate", "/nonexistent/workflow.yaml"])
        assert result.exit_code == 1
        assert "Error" in result.output


class TestLintCommand:
    def test_lint_gorgon_workflow(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(gorgon_workflow_path)])
        assert result.exit_code == 0
        assert "Score" in result.output

    def test_lint_json(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(gorgon_workflow_path), "--json"])
        assert result.exit_code == 0
        assert "score" in result.output

    def test_lint_filter_category(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(gorgon_workflow_path), "--category", "budget"])
        assert result.exit_code == 0

    def test_lint_invalid_category(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(
            app, ["lint", str(gorgon_workflow_path), "--category", "nonexistent"]
        )
        assert result.exit_code == 1
        assert "Unknown category" in result.output

    def test_lint_fail_under(self, gorgon_no_budget_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(gorgon_no_budget_path), "--fail-under", "100"])
        # No-budget workflow will have findings, score < 100.
        assert result.exit_code == 1
        assert "below threshold" in result.output

    def test_lint_fail_under_passes(self, gorgon_workflow_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(gorgon_workflow_path), "--fail-under", "1"])
        assert result.exit_code == 0

    def test_lint_missing_file(self) -> None:
        result = runner.invoke(app, ["lint", "/nonexistent/workflow.yaml"])
        assert result.exit_code == 1


class TestStatusCommand:
    def test_status_free(self) -> None:
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Free" in result.output
        assert "agent-audit" in result.output
