"""Regression tests for the last successful update sensor."""

from __future__ import annotations

from pathlib import Path

COORDINATOR_PATH = Path("custom_components/feuxdeforet_fr/coordinator.py")
SENSOR_PATH = Path("custom_components/feuxdeforet_fr/sensor.py")


def test_last_successful_update_is_recorded_and_exposed() -> None:
    """The timestamp must only advance after a complete successful refresh."""
    coordinator_source = COORDINATOR_PATH.read_text(encoding="utf-8")
    sensor_source = SENSOR_PATH.read_text(encoding="utf-8")

    assignment = "self.last_successful_update = dt_util.utcnow()"
    assert coordinator_source.index(assignment) < coordinator_source.index(
        "return data"
    )
    assert "always_update=True" in coordinator_source
    assert 'key="last_successful_update"' in sensor_source
    assert "available_after_failure=True" in sensor_source
