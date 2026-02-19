"""Output formatters for agent-audit (table, json, markdown)."""

from __future__ import annotations

import json as json_mod

from rich.console import Console
from rich.table import Table

from agent_audit.models import CompareResult, LintReport, Severity, WorkflowEstimate

_SEVERITY_STYLE: dict[Severity, str] = {
    Severity.ERROR: "[red]error[/red]",
    Severity.WARNING: "[yellow]warning[/yellow]",
    Severity.INFO: "[dim]info[/dim]",
}

_SEVERITY_ICON: dict[Severity, str] = {
    Severity.ERROR: "[red]x[/red]",
    Severity.WARNING: "[yellow]![/yellow]",
    Severity.INFO: "[dim]i[/dim]",
}


# ---------------------------------------------------------------------------
# Estimate formatters
# ---------------------------------------------------------------------------


def format_estimate_table(estimate: WorkflowEstimate, console: Console) -> None:
    """Print estimate as a Rich table."""
    console.print(f"\n[bold]WORKFLOW:[/bold] {estimate.workflow_name}")
    console.print(f"[bold]Provider:[/bold] {estimate.provider} / {estimate.model}")

    if estimate.budget_declared:
        console.print(f"[bold]Budget:[/bold] {estimate.budget_declared:,} tokens")
        if estimate.budget_utilization is not None:
            console.print(f"[bold]Utilization:[/bold] {estimate.budget_utilization}%")

    table = Table()
    table.add_column("Step", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Role")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Source", style="dim")

    for s in estimate.steps:
        table.add_row(
            s.step_id,
            s.step_type.value,
            s.role or "—",
            f"{s.estimated_tokens:,}",
            f"${s.cost_usd:.4f}",
            s.source,
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        "",
        f"[bold]{estimate.total_tokens:,}[/bold]",
        f"[bold green]${estimate.total_cost_usd:.4f}[/bold green]",
        "",
    )

    console.print(table)
    console.print()


def format_estimate_json(estimate: WorkflowEstimate, console: Console) -> None:
    """Print estimate as JSON."""
    console.print_json(
        json_mod.dumps(estimate.model_dump(mode="json", exclude_none=True), indent=2)
    )


def format_estimate_markdown(estimate: WorkflowEstimate, console: Console) -> None:
    """Print estimate as markdown table."""
    lines = [
        f"# {estimate.workflow_name}",
        f"**Provider:** {estimate.provider} / {estimate.model}",
        "",
        "| Step | Type | Role | Tokens | Cost | Source |",
        "|------|------|------|-------:|-----:|--------|",
    ]
    for s in estimate.steps:
        lines.append(
            f"| {s.step_id} | {s.step_type.value} | {s.role or '—'} "
            f"| {s.estimated_tokens:,} | ${s.cost_usd:.4f} | {s.source} |"
        )
    lines.append(
        f"| **TOTAL** | | | **{estimate.total_tokens:,}** | **${estimate.total_cost_usd:.4f}** | |"
    )
    console.print("\n".join(lines))


# ---------------------------------------------------------------------------
# Lint formatters
# ---------------------------------------------------------------------------


def format_lint_table(report: LintReport, console: Console) -> None:
    """Print lint report as a Rich table."""
    console.print(f"\n[bold]WORKFLOW:[/bold] {report.workflow_name}")

    if report.findings:
        table = Table()
        table.add_column("", width=3)
        table.add_column("Rule", style="dim")
        table.add_column("Severity")
        table.add_column("Step")
        table.add_column("Message")

        for f in report.findings:
            icon = _SEVERITY_ICON.get(f.severity, "")
            sev = _SEVERITY_STYLE.get(f.severity, f.severity.value)
            table.add_row(icon, f.rule_id, sev, f.step_id or "—", f.message)

        console.print(table)
    else:
        console.print("[green]No findings![/green]")

    # Summary.
    err = f"[red]{report.error_count} error(s)[/red]" if report.error_count else ""
    warn = f"[yellow]{report.warning_count} warning(s)[/yellow]" if report.warning_count else ""
    info = f"[dim]{report.info_count} info[/dim]" if report.info_count else ""
    parts = [p for p in (err, warn, info) if p]
    summary = ", ".join(parts) if parts else "[green]all clear[/green]"

    score_color = "green" if report.score >= 80 else "yellow" if report.score >= 50 else "red"
    console.print(
        f"\n[bold]Score:[/bold] [{score_color}]{report.score}/100[/{score_color}]  ({summary})"
    )
    console.print()


def format_lint_json(report: LintReport, console: Console) -> None:
    """Print lint report as JSON."""
    console.print_json(json_mod.dumps(report.model_dump(mode="json"), indent=2))


def format_lint_markdown(report: LintReport, console: Console) -> None:
    """Print lint report as markdown."""
    lines = [
        f"# Lint Report: {report.workflow_name}",
        f"**Score:** {report.score}/100",
        "",
    ]
    if report.findings:
        lines.extend(
            [
                "| Rule | Severity | Step | Message |",
                "|------|----------|------|---------|",
            ]
        )
        for f in report.findings:
            lines.append(f"| {f.rule_id} | {f.severity.value} | {f.step_id or '—'} | {f.message} |")
    else:
        lines.append("No findings.")
    console.print("\n".join(lines))


# ---------------------------------------------------------------------------
# Compare formatters
# ---------------------------------------------------------------------------


def format_compare_table(result: CompareResult, console: Console) -> None:
    """Print provider comparison as a Rich table."""
    console.print(f"\n[bold]COMPARE:[/bold] {result.workflow_name}")

    table = Table()
    table.add_column("Provider", style="cyan")
    table.add_column("Model")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")

    for est in result.estimates:
        style = "[bold]" if est.provider == result.cheapest else ""
        end = "[/bold]" if style else ""
        table.add_row(
            f"{style}{est.provider}{end}",
            est.model,
            f"{est.total_tokens:,}",
            f"${est.total_cost_usd:.4f}",
        )

    console.print(table)

    if result.savings_pct > 0:
        console.print(
            f"\n[green]Cheapest:[/green] {result.cheapest}  "
            f"[dim]({result.savings_pct}% savings vs {result.most_expensive})[/dim]"
        )
    console.print()


def format_compare_json(result: CompareResult, console: Console) -> None:
    """Print provider comparison as JSON."""
    console.print_json(json_mod.dumps(result.model_dump(mode="json"), indent=2))
