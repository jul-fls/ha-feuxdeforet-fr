"""Constants for the Feux de Foret integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "feuxdeforet_fr"
NAME = "Feux de Foret"
MANUFACTURER = "feuxdeforet.fr"

CONF_POLL_INTERVAL = "poll_interval"
CONF_CREATE_REGION_SENSORS = "create_region_sensors"
CONF_CREATE_DEPARTMENT_SENSORS = "create_department_sensors"
CONF_CREATE_FIRE_GEOLOCATIONS = "create_fire_geolocations"
CONF_GEOJSON_LAST_UPDATE = "geojson_last_update"
CONF_GEOJSON_NONCE = "geojson_nonce"

DEFAULT_POLL_INTERVAL = 300
MIN_POLL_INTERVAL = 60
DEFAULT_GEOJSON_LAST_UPDATE = "2026-07-05T00:11:12+02:00"
DEFAULT_GEOJSON_NONCE = "0"

DEFAULT_OPTIONS = {
    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
    CONF_CREATE_REGION_SENSORS: True,
    CONF_CREATE_DEPARTMENT_SENSORS: True,
    CONF_CREATE_FIRE_GEOLOCATIONS: True,
    CONF_GEOJSON_LAST_UPDATE: DEFAULT_GEOJSON_LAST_UPDATE,
    CONF_GEOJSON_NONCE: DEFAULT_GEOJSON_NONCE,
}

PLATFORMS = ["sensor", "geo_location"]
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_POLL_INTERVAL)

SERVICE_REFRESH = "refresh"
