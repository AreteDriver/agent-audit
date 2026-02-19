"""Lint rule registry and decorator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_audit.models import LintFinding, ParsedWorkflow, RuleCategory, Severity

# Type alias for rule functions.
RuleFunc = Callable[[ParsedWorkflow], list[LintFinding]]


@dataclass
class RuleEntry:
    """Registered lint rule metadata."""

    rule_id: str
    category: RuleCategory
    severity: Severity
    description: str
    func: RuleFunc


_RULE_REGISTRY: list[RuleEntry] = []


def lint_rule(
    rule_id: str,
    category: RuleCategory,
    severity: Severity,
    description: str,
) -> Callable[[RuleFunc], RuleFunc]:
    """Decorator to register a lint rule function."""

    def decorator(func: RuleFunc) -> RuleFunc:
        _RULE_REGISTRY.append(
            RuleEntry(
                rule_id=rule_id,
                category=category,
                severity=severity,
                description=description,
                func=func,
            )
        )
        return func

    return decorator


def get_all_rules() -> list[RuleEntry]:
    """Return all registered lint rules."""
    return list(_RULE_REGISTRY)


def get_rules_by_category(category: RuleCategory) -> list[RuleEntry]:
    """Return rules filtered by category."""
    return [r for r in _RULE_REGISTRY if r.category == category]
