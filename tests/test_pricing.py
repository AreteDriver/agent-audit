"""Tests for agent_audit.pricing."""

from __future__ import annotations

import pytest

from agent_audit.exceptions import PricingError
from agent_audit.models import ModelPricing
from agent_audit.pricing import (
    calculate_cost,
    get_model_pricing,
    list_models,
    list_providers,
    load_providers,
    reset_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    reset_cache()


class TestLoadProviders:
    def test_loads_bundled_pricing(self) -> None:
        providers = load_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "ollama" in providers

    def test_anthropic_has_models(self) -> None:
        providers = load_providers()
        anthropic = providers["anthropic"]
        assert "claude-sonnet-4" in anthropic.models
        assert "claude-opus-4" in anthropic.models
        assert anthropic.default_model == "claude-sonnet-4"

    def test_openai_has_models(self) -> None:
        providers = load_providers()
        openai = providers["openai"]
        assert "gpt-4o" in openai.models
        assert openai.default_model == "gpt-4o"

    def test_ollama_is_free(self) -> None:
        providers = load_providers()
        ollama = providers["ollama"]
        for model in ollama.models.values():
            assert model.input_price_per_1k == 0.0
            assert model.output_price_per_1k == 0.0


class TestGetModelPricing:
    def test_default_model(self) -> None:
        pricing = get_model_pricing("anthropic")
        assert pricing.name == "claude-sonnet-4"
        assert pricing.input_price_per_1k == 0.003

    def test_specific_model(self) -> None:
        pricing = get_model_pricing("anthropic", "claude-opus-4")
        assert pricing.name == "claude-opus-4"
        assert pricing.input_price_per_1k == 0.015

    def test_unknown_provider(self) -> None:
        with pytest.raises(PricingError, match="Unknown provider"):
            get_model_pricing("nonexistent")

    def test_unknown_model(self) -> None:
        with pytest.raises(PricingError, match="Unknown model"):
            get_model_pricing("anthropic", "claude-99")


class TestCalculateCost:
    def test_basic_calculation(self) -> None:
        pricing = ModelPricing(
            name="test",
            provider="test",
            input_price_per_1k=0.003,
            output_price_per_1k=0.015,
        )
        cost = calculate_cost(1000, 1000, pricing)
        assert cost == 0.018  # 0.003 + 0.015

    def test_zero_tokens(self) -> None:
        pricing = ModelPricing(
            name="test",
            provider="test",
            input_price_per_1k=0.003,
            output_price_per_1k=0.015,
        )
        assert calculate_cost(0, 0, pricing) == 0.0

    def test_free_provider(self) -> None:
        pricing = ModelPricing(
            name="test",
            provider="ollama",
            input_price_per_1k=0.0,
            output_price_per_1k=0.0,
        )
        assert calculate_cost(10000, 10000, pricing) == 0.0

    def test_sonnet_realistic(self) -> None:
        pricing = get_model_pricing("anthropic", "claude-sonnet-4")
        # 1500 input + 3500 output
        cost = calculate_cost(1500, 3500, pricing)
        expected = (1500 / 1000) * 0.003 + (3500 / 1000) * 0.015
        assert abs(cost - expected) < 0.0001


class TestListProviders:
    def test_returns_sorted(self) -> None:
        providers = list_providers()
        assert providers == sorted(providers)
        assert "anthropic" in providers


class TestListModels:
    def test_returns_models(self) -> None:
        models = list_models("anthropic")
        assert "claude-sonnet-4" in models

    def test_unknown_provider(self) -> None:
        assert list_models("nonexistent") == []
