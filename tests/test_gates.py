"""Tests for agent_audit.gates."""

from __future__ import annotations

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from agent_audit.gates import require_pro
from agent_audit.licensing import _compute_check_segment

runner = CliRunner()


def _make_valid_key() -> str:
    body = "TEST-ABCD"
    check = _compute_check_segment(body)
    return f"AAUD-{body}-{check}"


class TestRequirePro:
    def test_blocks_free_tier(self) -> None:
        app = typer.Typer()

        @app.command()
        @require_pro("compare")
        def cmd() -> None:
            pass

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            result = runner.invoke(app, [])
            assert result.exit_code == 1
            assert "compare" in result.output

    def test_allows_pro_tier(self) -> None:
        app = typer.Typer()

        @app.command()
        @require_pro("compare")
        def cmd() -> None:
            print("success")

        key = _make_valid_key()
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": key}):
            result = runner.invoke(app, [])
            assert result.exit_code == 0
            assert "success" in result.output

    def test_preserves_function_name(self) -> None:
        @require_pro("compare")
        def my_func() -> None:
            """My docstring."""

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My docstring."

    def test_upgrade_message_shown(self) -> None:
        app = typer.Typer()

        @app.command()
        @require_pro("markdown_export")
        def cmd() -> None:
            pass

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            result = runner.invoke(app, [])
            assert "AGENT_AUDIT_LICENSE" in result.output
