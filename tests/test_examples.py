"""Validate the bundled Home Assistant YAML examples."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_all_yaml_examples_are_valid() -> None:
    """Every example must remain valid YAML."""
    for path in Path("examples").glob("*.yaml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8")) is not None
