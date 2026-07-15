"""Regression tests for dynamic fire entity cleanup."""

from __future__ import annotations

from pathlib import Path

GEO_LOCATION_PATH = Path("custom_components/feuxdeforet_fr/geo_location.py")
CONST_PATH = Path("custom_components/feuxdeforet_fr/const.py")


def test_missing_fire_entities_are_removed_immediately() -> None:
    """A fire absent from the latest payload must not remain as unknown."""
    source = GEO_LOCATION_PATH.read_text(encoding="utf-8")
    constants = CONST_PATH.read_text(encoding="utf-8")

    assert "missing_since" not in source
    assert "FIRE_REMOVAL_GRACE_PERIOD" not in source
    assert "FIRE_REMOVAL_GRACE_PERIOD" not in constants
    assert "entity.async_remove(force_remove=True)" in source
