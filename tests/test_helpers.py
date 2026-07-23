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
build_department_names = helpers.build_department_names
build_department_to_region = helpers.build_department_to_region
build_region_counts = helpers.build_region_counts
canonical_department_slug = helpers.canonical_department_slug
department_code_from_slug = helpers.department_code_from_slug
department_match_key = helpers.department_match_key
department_slug_from_url = helpers.department_slug_from_url
features_from_geojson = helpers.features_from_geojson
fire_proximity = helpers.fire_proximity
home_fires_from_data = helpers.home_fires_from_data
is_active_fire = helpers.is_active_fire
is_displayable_fire_location = helpers.is_displayable_fire_location
municipality_from_url = helpers.municipality_from_url
normalize_status = helpers.normalize_status
snapshot_consistency_issues = helpers.snapshot_consistency_issues


def test_fire_location_requires_an_operational_state() -> None:
    """Incomplete probable points must not create map entities."""
    assert is_displayable_fire_location(SimpleNamespace(state="attaque"))
    assert not is_displayable_fire_location(SimpleNamespace(state=None))
    assert not is_displayable_fire_location(SimpleNamespace(state="  "))


def test_snapshot_consistency_rejects_empty_or_contradictory_updates() -> None:
    """Broken upstream snapshots cannot replace the last coherent HA data."""
    active_home_fire = SimpleNamespace(in_progress=True)
    populated_geojson = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature"}],
    }

    assert snapshot_consistency_issues(
        SimpleNamespace(valid_published=2),
        (),
        {"type": "FeatureCollection", "features": []},
    ) == ("GeoJSON is empty while statistics report active fires",)
    assert snapshot_consistency_issues(
        SimpleNamespace(valid_published=0),
        (active_home_fire,),
        populated_geojson,
    ) == ("statistics report zero while active fires are listed",)
    assert snapshot_consistency_issues(
        SimpleNamespace(valid_published=1),
        (active_home_fire,),
        populated_geojson,
    ) == ()


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
    assert canonical_department_slug("haute-loire-43") == "haute-loire"
    assert department_match_key("cotes-d-armor-22") == department_match_key(
        "cotes-darmor"
    )


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

    fires = features_from_geojson(
        payload,
        {"hauteloire": "auvergne-rhone-alpes"},
        {"hauteloire": "Haute-Loire"},
    )

    assert list(fires) == ["1533"]
    fire = fires["1533"]
    assert fire.latitude == 44.846703
    assert fire.longitude == 3.757945
    assert fire.department_slug == "haute-loire"
    assert fire.region_slug == "auvergne-rhone-alpes"
    assert fire.municipality == "Saint Haon"
    assert fire.department_name == "Haute-Loire"
    assert fire.department_code == "43"
    assert fire.name == "Feu de Saint Haon - Haute-Loire (43)"
    assert is_active_fire(fire)


def test_geometry_collection_fire_uses_point_and_reports_perimeter() -> None:
    """A point plus fire perimeter remains usable as a geo-location."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "GeometryCollection",
                    "geometries": [
                        {
                            "type": "Point",
                            "coordinates": [-1.015069, 44.906987],
                        },
                        {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [-1.1, 44.8],
                                    [-1.0, 44.9],
                                    [-1.1, 44.8],
                                ]
                            ],
                        },
                    ],
                },
                "properties": {
                    "id": "4367",
                    "statut": "valide_publie",
                    "etat": "attaque",
                    "url": (
                        "https://feuxdeforet.fr/"
                        "gironde-33/saumos-22-07-2026-4367/"
                    ),
                },
            }
        ],
    }

    fires = features_from_geojson(
        payload,
        {"gironde": "nouvelle-aquitaine"},
        {"gironde": "Gironde"},
    )

    fire = fires["4367"]
    assert fire.longitude == -1.015069
    assert fire.latitude == 44.906987
    assert fire.name == "Feu de Saumos - Gironde (33)"
    assert fire.state == "attaque"
    assert fire.perimeter_count == 1
    assert is_displayable_fire_location(fire)


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

    fires = features_from_geojson(
        payload,
        {"var": "provence-alpes-cote-d-azur"},
        {"var": "Var"},
    )

    assert fires["1"].name == "Feu de Toulon - Var (83) #1"
    assert fires["2"].name == "Feu de Toulon - Var (83) #2"


def test_closed_status_is_exposed_as_extinguished() -> None:
    """Closed API fires use an unambiguous user-facing status."""
    assert normalize_status("cloture") == "eteint"
    assert normalize_status("valide_publie") == "valide_publie"
    assert normalize_status(None) is None


def test_zone_counts() -> None:
    """Region and department counts include active and status breakdowns."""
    department = SimpleNamespace(
        slug="haute-loire",
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
    assert department_counts["haute-loire"].active_count == 1
    assert department_counts["haute-loire"].by_status == {
        "valide_publie": 1,
        "douteux": 1,
    }


def test_fixed_and_controlled_published_fires_are_current() -> None:
    """All published fires count as current regardless of operational state."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"coordinates": [3.0, 44.0]},
                "properties": {
                    "id": state,
                    "statut": "valide_publie",
                    "etat": state,
                    "url": f"https://feuxdeforet.fr/landes-40/{state}/",
                },
            }
            for state in ("attaque", "fixe", "maitrise")
        ],
    }
    fires = features_from_geojson(payload, {"landes": "nouvelle-aquitaine"})

    assert all(fire.region_slug == "nouvelle-aquitaine" for fire in fires.values())
    assert all(is_active_fire(fire) for fire in fires.values())


def test_home_fires_are_parsed_from_raw_home_payload() -> None:
    """Homepage recent fires are normalized from the library's retained payload."""
    home = SimpleNamespace(
        raw={
            "feux": [
                {
                    "id": 3057,
                    "title": "Incendie à Rodelle (12)",
                    "commune": "Rodelle",
                    "dept": "12",
                    "url": "/aveyron-12/rodelle/",
                    "dateIso": "2026-07-14T21:32:35Z",
                    "timeAgo": "il y a 18 minutes",
                    "enCours": True,
                    "thumbnail": "/medias/rodelle.webp",
                }
            ]
        }
    )

    fires = home_fires_from_data(home)

    assert len(fires) == 1
    assert fires[0].municipality == "Rodelle"
    assert fires[0].in_progress
    assert fires[0].url == "https://feuxdeforet.fr/aveyron-12/rodelle/"
    assert fires[0].thumbnail == "https://feuxdeforet.fr/medias/rodelle.webp"


def test_fire_proximity_uses_only_active_fires() -> None:
    """Nearest and nearby calculations ignore non-published map entries."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"coordinates": [2.36, 48.86]},
                "properties": {
                    "id": "near",
                    "statut": "valide_publie",
                    "url": "https://feuxdeforet.fr/paris-75/paris/",
                },
            },
            {
                "geometry": {"coordinates": [4.84, 45.76]},
                "properties": {
                    "id": "far",
                    "statut": "valide_publie",
                    "url": "https://feuxdeforet.fr/rhone-69/lyon/",
                },
            },
            {
                "geometry": {"coordinates": [2.35, 48.85]},
                "properties": {
                    "id": "closed",
                    "statut": "cloture",
                    "url": "https://feuxdeforet.fr/paris-75/paris/",
                },
            },
        ],
    }
    fires = features_from_geojson(payload, {})

    nearest_id, nearest_distance, nearby_ids = fire_proximity(
        fires, 48.8566, 2.3522, 10
    )

    assert nearest_id == "near"
    assert nearest_distance is not None and nearest_distance < 1
    assert nearby_ids == ("near",)
