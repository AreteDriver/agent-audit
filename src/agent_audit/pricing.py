"""Provider pricing loader and cost calculator."""

from __future__ import annotations

import logging

import yaml

from agent_audit.config import PROVIDERS_FILE
from agent_audit.exceptions import PricingError
from agent_audit.models import ModelPricing, ProviderConfig

logger = logging.getLogger(__name__)

_cached_providers: dict[str, ProviderConfig] | None = None


def load_providers(path: str | None = None) -> dict[str, ProviderConfig]:
    """Load provider pricing from YAML. Caches after first load."""
    global _cached_providers  # noqa: PLW0603
    if _cached_providers is not None and path is None:
        return _cached_providers

    pricing_path = PROVIDERS_FILE if path is None else __import__("pathlib").Path(path)
    try:
        raw = yaml.safe_load(pricing_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PricingError(f"Failed to load pricing data: {exc}") from exc

    providers_raw = raw.get("providers", {})
    if not isinstance(providers_raw, dict):
        raise PricingError("Invalid pricing data: 'providers' must be a mapping")

    result: dict[str, ProviderConfig] = {}
    for provider_name, provider_data in providers_raw.items():
        if not isinstance(provider_data, dict):
            continue
        models: dict[str, ModelPricing] = {}
        for model_name, model_data in provider_data.get("models", {}).items():
            if not isinstance(model_data, dict):
                continue
            models[model_name] = ModelPricing(
                name=model_name,
                provider=provider_name,
                input_price_per_1k=float(model_data.get("input", 0)),
                output_price_per_1k=float(model_data.get("output", 0)),
                context_window=int(model_data.get("context", 0)),
                notes=str(model_data.get("notes", "")),
            )
        result[provider_name] = ProviderConfig(
            name=provider_name,
            models=models,
            default_model=str(provider_data.get("default_model", "")),
        )

    if path is None:
        _cached_providers = result
    return result


def reset_cache() -> None:
    """Clear the cached provider data (useful for testing)."""
    global _cached_providers  # noqa: PLW0603
    _cached_providers = None


def get_model_pricing(
    provider: str,
    model: str | None = None,
    *,
    providers: dict[str, ProviderConfig] | None = None,
) -> ModelPricing:
    """Look up pricing for a specific provider/model."""
    if providers is None:
        providers = load_providers()

    config = providers.get(provider)
    if config is None:
        raise PricingError(f"Unknown provider: {provider!r}")

    model_name = model or config.default_model
    pricing = config.models.get(model_name)
    if pricing is None:
        raise PricingError(
            f"Unknown model {model_name!r} for provider {provider!r}. "
            f"Available: {', '.join(config.models)}"
        )
    return pricing


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: ModelPricing,
) -> float:
    """Calculate cost in USD for given token counts."""
    input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
    output_cost = (output_tokens / 1000) * pricing.output_price_per_1k
    return round(input_cost + output_cost, 6)


def list_providers(
    *,
    providers: dict[str, ProviderConfig] | None = None,
) -> list[str]:
    """Return available provider names."""
    if providers is None:
        providers = load_providers()
    return sorted(providers.keys())


def list_models(
    provider: str,
    *,
    providers: dict[str, ProviderConfig] | None = None,
) -> list[str]:
    """Return available model names for a provider."""
    if providers is None:
        providers = load_providers()
    config = providers.get(provider)
    if config is None:
        return []
    return sorted(config.models.keys())
