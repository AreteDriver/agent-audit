"""Licensing and tier management for agent-lint.

Validates license keys locally (format + HMAC checksum), then optionally
against the shared license server at cmdf-license.fly.dev for full validation.
Falls back gracefully to local-only validation if the server is unreachable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_KEY_SALT = "agent-lint-v1"

_LICENSE_LOCATIONS: list[str] = [
    ".agent-lint-license",
    "~/.config/agent-lint/license",
    "~/.agent-lint/license",
    "~/.agent-lint-license",
]

_ENV_LICENSE_KEY = "AGENT_LINT_LICENSE"
_ENV_LICENSE_SERVER = "AGENT_LINT_LICENSE_SERVER"
_DEFAULT_LICENSE_SERVER = "https://cmdf-license.fly.dev"
_PRODUCT = "agent-lint"

_CACHE_DIR = Path("~/.agent-lint").expanduser()
_CACHE_FILE = _CACHE_DIR / "license_cache.json"
_CACHE_TTL_SECONDS = 86400  # 24 hours


class Tier(StrEnum):
    """Product tier levels."""

    FREE = "free"
    PRO = "pro"


class TierConfig(BaseModel):
    """Configuration for a product tier."""

    name: str
    price_label: str
    features: list[str]


TIER_DEFINITIONS: dict[Tier, TierConfig] = {
    Tier.FREE: TierConfig(
        name="Free",
        price_label="Free forever",
        features=[
            "estimate",
            "lint",
            "status",
        ],
    ),
    Tier.PRO: TierConfig(
        name="Pro",
        price_label="$8/mo",
        features=[
            "estimate",
            "lint",
            "status",
            "compare",
            "markdown_export",
            "custom_pricing",
            "custom_rules",
            "historical_tracking",
        ],
    ),
}

PRO_FEATURES: frozenset[str] = frozenset(
    {
        "compare",
        "markdown_export",
        "custom_pricing",
        "custom_rules",
        "historical_tracking",
    }
)


class LicenseInfo(BaseModel):
    """Validated license information."""

    tier: Tier = Tier.FREE
    license_key: str | None = None
    valid: bool = False
    degraded: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


def _validate_key_format(key: str) -> bool:
    """Check if a license key matches ``ALNT-XXXX-XXXX-XXXX``."""
    key = key.strip()
    if not key.startswith("ALNT-"):
        return False
    parts = key.split("-")
    if len(parts) != 4:
        return False
    for part in parts[1:]:
        if len(part) != 4 or not part.isalnum() or not part.isupper():
            return False
    return True


def _compute_check_segment(body: str) -> str:
    """Derive the check segment from the key body."""
    digest = hashlib.sha256(f"{_KEY_SALT}:{body}".encode()).hexdigest()
    return digest[:4].upper()


def _validate_key_checksum(key: str) -> bool:
    """Verify the last segment matches the HMAC-derived value."""
    parts = key.strip().split("-")
    if len(parts) != 4:
        return False
    body = f"{parts[1]}-{parts[2]}"
    expected = _compute_check_segment(body)
    return parts[3] == expected


def _find_license_key() -> str | None:
    """Search for a license key in environment and filesystem."""
    env_key = os.environ.get(_ENV_LICENSE_KEY)
    if env_key and env_key.strip():
        return env_key.strip()

    for location in _LICENSE_LOCATIONS:
        path = Path(location).expanduser()
        if path.is_file():
            try:
                content = path.read_text().strip()
                if content:
                    return content
            except OSError:
                continue

    return None


def _get_machine_id() -> str:
    """Generate a stable machine identifier (hostname + username hash)."""
    import platform

    raw = f"{platform.node()}:{os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _read_cache() -> dict[str, Any] | None:
    """Read cached license validation result if fresh."""
    try:
        if not _CACHE_FILE.is_file():
            return None
        data = json.loads(_CACHE_FILE.read_text())
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > _CACHE_TTL_SECONDS:
            return None
        return data
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _write_cache(data: dict[str, Any]) -> None:
    """Write license validation result to cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data["cached_at"] = time.time()
        _CACHE_FILE.write_text(json.dumps(data))
        _CACHE_FILE.chmod(0o600)
    except OSError:
        pass


def _validate_server(key: str) -> dict[str, Any] | None:
    """Validate key against the license server. Returns None on failure."""
    try:
        import httpx
    except ImportError:
        return None

    server = os.environ.get(_ENV_LICENSE_SERVER, _DEFAULT_LICENSE_SERVER)

    try:
        resp = httpx.post(
            f"{server}/v1/validate",
            json={
                "license_key": key,
                "product": _PRODUCT,
                "machine_id": _get_machine_id(),
            },
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        logger.debug("License server unreachable, falling back to local validation")

    return None


def get_license_info() -> LicenseInfo:
    """Detect and validate the current license.

    Validation pipeline:
    1. Find key (env var / file)
    2. Local format + checksum check
    3. Check fresh cache (24h TTL)
    4. Call license server (5s timeout)
    5. Server down → use expired cache with degraded flag
    6. No cache → local-only validation (Pro if checksum passes)
    """
    key = _find_license_key()

    if key is None:
        return LicenseInfo(tier=Tier.FREE)

    if not _validate_key_format(key):
        logger.warning("Invalid license key format")
        return LicenseInfo(tier=Tier.FREE, license_key=key, valid=False)

    if not _validate_key_checksum(key):
        logger.warning("License key checksum mismatch")
        return LicenseInfo(tier=Tier.FREE, license_key=key, valid=False)

    # Check fresh cache
    cached = _read_cache()
    if cached and cached.get("key") == key:
        return LicenseInfo(
            tier=Tier(cached.get("tier", "pro")),
            license_key=key,
            valid=cached.get("valid", True),
            metadata=cached.get("metadata", {}),
        )

    # Try server validation
    server_result = _validate_server(key)
    if server_result is not None:
        tier = Tier(server_result.get("tier", "pro"))
        valid = server_result.get("valid", False)
        metadata = server_result.get("metadata", {})
        _write_cache(
            {
                "key": key,
                "tier": tier.value,
                "valid": valid,
                "metadata": metadata,
            }
        )
        result_tier = tier if valid else Tier.FREE
        return LicenseInfo(tier=result_tier, license_key=key, valid=valid, metadata=metadata)

    # Server unreachable — try expired cache
    expired = _read_cache.__wrapped__() if hasattr(_read_cache, "__wrapped__") else None
    if expired is None:
        # Read cache ignoring TTL
        try:
            if _CACHE_FILE.is_file():
                data = json.loads(_CACHE_FILE.read_text())
                if data.get("key") == key:
                    return LicenseInfo(
                        tier=Tier(data.get("tier", "pro")),
                        license_key=key,
                        valid=data.get("valid", True),
                        degraded=True,
                        metadata=data.get("metadata", {}),
                    )
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    # Local-only fallback — checksum passed, grant Pro
    return LicenseInfo(tier=Tier.PRO, license_key=key, valid=True, degraded=True)


def has_feature(feature: str) -> bool:
    """Check if the current license grants access to a feature."""
    info = get_license_info()
    tier_config = TIER_DEFINITIONS[info.tier]
    return feature in tier_config.features


def is_pro() -> bool:
    """Check if the current license is Pro tier."""
    return get_license_info().tier == Tier.PRO


def get_upgrade_message(feature: str) -> str:
    """Return a user-facing upgrade prompt for a gated feature."""
    pro_config = TIER_DEFINITIONS[Tier.PRO]
    return (
        f"'{feature}' requires agent-lint Pro ({pro_config.price_label}).\n"
        f"Set your key via: export {_ENV_LICENSE_KEY}=ALNT-XXXX-XXXX-XXXX"
    )
