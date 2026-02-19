"""Tests for agent_audit.licensing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agent_audit.licensing import (
    PRO_FEATURES,
    TIER_DEFINITIONS,
    Tier,
    _compute_check_segment,
    _find_license_key,
    _validate_key_checksum,
    _validate_key_format,
    get_license_info,
    get_upgrade_message,
    has_feature,
    is_pro,
)


def _make_valid_key() -> str:
    """Build a valid AAUD license key with correct checksum."""
    body = "TEST-ABCD"
    check = _compute_check_segment(body)
    return f"AAUD-{body}-{check}"


class TestKeyFormat:
    def test_valid_format(self) -> None:
        assert _validate_key_format("AAUD-ABCD-EFGH-IJKL")

    def test_wrong_prefix(self) -> None:
        assert not _validate_key_format("MCPM-ABCD-EFGH-IJKL")

    def test_too_few_parts(self) -> None:
        assert not _validate_key_format("AAUD-ABCD-EFGH")

    def test_too_many_parts(self) -> None:
        assert not _validate_key_format("AAUD-ABCD-EFGH-IJKL-MNOP")

    def test_lowercase_rejected(self) -> None:
        assert not _validate_key_format("AAUD-abcd-EFGH-IJKL")

    def test_wrong_length(self) -> None:
        assert not _validate_key_format("AAUD-ABC-EFGH-IJKL")

    def test_strips_whitespace(self) -> None:
        assert _validate_key_format("  AAUD-ABCD-EFGH-IJKL  ")


class TestKeyChecksum:
    def test_valid_checksum(self) -> None:
        key = _make_valid_key()
        assert _validate_key_checksum(key)

    def test_invalid_checksum(self) -> None:
        assert not _validate_key_checksum("AAUD-TEST-ABCD-ZZZZ")

    def test_bad_format_fails(self) -> None:
        assert not _validate_key_checksum("AAUD-AB")


class TestComputeCheckSegment:
    def test_deterministic(self) -> None:
        a = _compute_check_segment("TEST-ABCD")
        b = _compute_check_segment("TEST-ABCD")
        assert a == b

    def test_four_chars_uppercase(self) -> None:
        seg = _compute_check_segment("XXXX-YYYY")
        assert len(seg) == 4
        assert seg == seg.upper()


class TestFindLicenseKey:
    def test_env_var(self) -> None:
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": "AAUD-AAAA-BBBB-CCCC"}):
            assert _find_license_key() == "AAUD-AAAA-BBBB-CCCC"

    def test_env_var_strips(self) -> None:
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": "  AAUD-AAAA-BBBB-CCCC  "}):
            assert _find_license_key() == "AAUD-AAAA-BBBB-CCCC"

    def test_env_var_empty(self) -> None:
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": ""}, clear=False):
            result = _find_license_key()
            # Empty env var falls through to file search.
            assert result is None or result != ""

    def test_file_fallback(self, tmp_path: Path) -> None:
        license_file = tmp_path / ".agent-audit-license"
        key = _make_valid_key()
        license_file.write_text(key)

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "agent_audit.licensing._LICENSE_LOCATIONS",
                [str(license_file)],
            ),
        ):
            assert _find_license_key() == key

    def test_no_key_anywhere(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", ["/nonexistent/path"]),
        ):
            assert _find_license_key() is None


class TestGetLicenseInfo:
    def test_no_key_free(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            info = get_license_info()
            assert info.tier == Tier.FREE
            assert not info.valid

    def test_valid_key_pro(self) -> None:
        key = _make_valid_key()
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": key}):
            info = get_license_info()
            assert info.tier == Tier.PRO
            assert info.valid
            assert info.license_key == key

    def test_bad_format_stays_free(self) -> None:
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": "bad-key"}):
            info = get_license_info()
            assert info.tier == Tier.FREE
            assert not info.valid

    def test_bad_checksum_stays_free(self) -> None:
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": "AAUD-TEST-ABCD-ZZZZ"}):
            info = get_license_info()
            assert info.tier == Tier.FREE
            assert not info.valid


class TestHasFeature:
    def test_free_has_estimate(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            assert has_feature("estimate")

    def test_free_lacks_compare(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            assert not has_feature("compare")

    def test_pro_has_compare(self) -> None:
        key = _make_valid_key()
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": key}):
            assert has_feature("compare")


class TestIsPro:
    def test_free_tier(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_audit.licensing._LICENSE_LOCATIONS", []),
        ):
            assert not is_pro()

    def test_pro_tier(self) -> None:
        key = _make_valid_key()
        with patch.dict("os.environ", {"AGENT_AUDIT_LICENSE": key}):
            assert is_pro()


class TestTierDefinitions:
    def test_free_features(self) -> None:
        free = TIER_DEFINITIONS[Tier.FREE]
        assert "estimate" in free.features
        assert "lint" in free.features
        assert "compare" not in free.features

    def test_pro_features(self) -> None:
        pro = TIER_DEFINITIONS[Tier.PRO]
        assert "compare" in pro.features
        assert "estimate" in pro.features

    def test_pro_features_frozenset(self) -> None:
        for f in PRO_FEATURES:
            assert f in TIER_DEFINITIONS[Tier.PRO].features


class TestUpgradeMessage:
    def test_contains_feature(self) -> None:
        msg = get_upgrade_message("compare")
        assert "compare" in msg

    def test_contains_env_var(self) -> None:
        msg = get_upgrade_message("compare")
        assert "AGENT_AUDIT_LICENSE" in msg

    def test_contains_price(self) -> None:
        msg = get_upgrade_message("compare")
        assert "$8/mo" in msg
