"""Custom exceptions for agent-lint."""

from __future__ import annotations


class AgentAuditError(Exception):
    """Base exception for all agent-lint errors."""


class ParseError(AgentAuditError):
    """Workflow YAML parsing failed."""


class EstimateError(AgentAuditError):
    """Cost estimation failed."""


class LintError(AgentAuditError):
    """Linting failed unexpectedly."""


class PricingError(AgentAuditError):
    """Pricing data load or calculation failed."""


class LicenseError(AgentAuditError):
    """Feature requires a higher license tier."""
