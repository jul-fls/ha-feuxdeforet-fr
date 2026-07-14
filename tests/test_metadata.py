"""Validate integration metadata and translations."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

COMPONENT = Path("custom_components/feuxdeforet_fr")


def _read_json(path: Path) -> dict:
    """Read one JSON metadata file."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_versions_are_synchronized() -> None:
    """Manifest and project versions must be released together."""
    manifest = _read_json(COMPONENT / "manifest.json")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["version"] == project["project"]["version"]


def test_translations_cover_all_entities_and_options() -> None:
    """French and English translations must cover the source string keys."""
    source = _read_json(COMPONENT / "strings.json")
    for language in ("en", "fr"):
        translation = _read_json(COMPONENT / "translations" / f"{language}.json")
        assert translation["entity"].keys() == source["entity"].keys()
        for platform, entities in source["entity"].items():
            assert translation["entity"][platform].keys() == entities.keys()
        assert (
            translation["options"]["step"]["init"]["data"].keys()
            == source["options"]["step"]["init"]["data"].keys()
        )
