"""Tests for Feux de Foret helper functions."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "feuxdeforet_fr"

package = ModuleType("custom_components.feuxdeforet_fr")
package.__path__ = [str(PACKAGE_PATH)]  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components.feuxdeforet_fr", package)

helpers = importlib.import_module("custom_components.feuxdeforet_fr.helpers")

build_department_counts = helpers.build_department_counts
build_department_to_region = helpers.build_department_to_region
build_region_counts = helpers.build_region_counts
department_code_from_slug = helpers.department_code_from_slug
department_slug_from_url = helpers.department_slug_from_url
features_from_geojson = helpers.features_from_geojson
is_active_fire = helpers.is_active_fire
municipality_from_url = helpers.municipality_from_url


def test_department_slug_from_url() -> None:
    """Department slug is extracted from absolute fire URLs."""
    assert (
        department_slug_from_url(
            "https://feuxdeforet.fr/haute-loire-43/saint-haon-05-07-2026-1533/"
        )
        == "haute-loire-43"
    )
    assert department_slug_from_url(None) is None


def test_fire_location_labels_from_url() -> None:
    """Fire URLs are converted to user-friendly labels."""
    url = "https://feuxdeforet.fr/haute-loire-43/saint-haon-05-07-2026-1533/"

    assert municipality_from_url(url) == "Saint Haon"
    assert department_code_from_slug("haute-loire-43") == "43"


def test_features_from_wrapped_geojson() -> None:
    """GeoJSON API envelope is parsed into fire features."""
    payload = {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [3.757945, 44.846703],
                    },
                    "properties": {
                        "id": "1533",
                        "statut": "valide_publie",
                        "etat": "attaque",
                        "url": "https://feuxdeforet.fr/haute-loire-43/saint-haon-05-07-2026-1533/",
                    },
                }
            ],
        }
    }

    fires = features_from_geojson(payload, {"haute-loire-43": "auvergne-rhone-alpes"})

    assert list(fires) == ["1533"]
    fire = fires["1533"]
    assert fire.latitude == 44.846703
    assert fire.longitude == 3.757945
    assert fire.department_slug == "haute-loire-43"
    assert fire.region_slug == "auvergne-rhone-alpes"
    assert fire.municipality == "Saint Haon"
    assert fire.department_code == "43"
    assert fire.name == "Feu de Saint Haon - 43"
    assert is_active_fire(fire)


def test_duplicate_fire_labels_get_fire_id_suffix() -> None:
    """Duplicate municipality labels are disambiguated with the fire id."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"coordinates": [3.0, 44.0]},
                "properties": {
                    "id": "1",
                    "statut": "valide_publie",
                    "url": "https://feuxdeforet.fr/var-83/toulon-01-07-2026-1/",
                },
            },
            {
                "geometry": {"coordinates": [3.1, 44.1]},
                "properties": {
                    "id": "2",
                    "statut": "valide_publie",
                    "url": "https://feuxdeforet.fr/var-83/toulon-01-07-2026-2/",
                },
            },
        ],
    }

    fires = features_from_geojson(payload, {"var-83": "provence-alpes-cote-d-azur"})

    assert fires["1"].name == "Feu de Toulon - 83 #1"
    assert fires["2"].name == "Feu de Toulon - 83 #2"


def test_zone_counts() -> None:
    """Region and department counts include active and status breakdowns."""
    department = SimpleNamespace(
        slug="haute-loire-43",
        name="Haute-Loire",
        url="/auvergne-rhone-alpes/haute-loire/",
    )
    region = SimpleNamespace(
        slug="auvergne-rhone-alpes",
        name="Auvergne-Rhone-Alpes",
        url="/auvergne-rhone-alpes/",
        departments=(department,),
    )
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"coordinates": [3.0, 44.0]},
                "properties": {
                    "id": "1",
                    "statut": "valide_publie",
                    "etat": "attaque",
                    "url": "https://feuxdeforet.fr/haute-loire-43/foo/",
                },
            },
            {
                "geometry": {"coordinates": [4.0, 45.0]},
                "properties": {
                    "id": "2",
                    "statut": "douteux",
                    "url": "https://feuxdeforet.fr/haute-loire-43/bar/",
                },
            },
        ],
    }
    regions = (region,)
    fires = features_from_geojson(payload, build_department_to_region(regions))

    region_counts = build_region_counts(regions, fires)
    department_counts = build_department_counts(regions, fires)

    assert region_counts["auvergne-rhone-alpes"].count == 2
    assert region_counts["auvergne-rhone-alpes"].active_count == 1
    assert department_counts["haute-loire-43"].by_status == {
        "valide_publie": 1,
        "douteux": 1,
    }
