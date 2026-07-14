"""Constants for the Feux de Foret integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "feuxdeforet_fr"
NAME = "Feux de Foret"
MANUFACTURER = "feuxdeforet.fr"
DEVICE_ID = "france"
DEVICE_NAME = "Feux de Foret"

CONF_POLL_INTERVAL = "poll_interval"
CONF_CREATE_REGION_SENSORS = "create_region_sensors"
CONF_CREATE_DEPARTMENT_SENSORS = "create_department_sensors"
CONF_CREATE_FIRE_GEOLOCATIONS = "create_fire_geolocations"
CONF_PROXIMITY_RADIUS_KM = "proximity_radius_km"

DEFAULT_POLL_INTERVAL = 300
MIN_POLL_INTERVAL = 60
DEFAULT_PROXIMITY_RADIUS_KM = 25
GEOJSON_NONCE = "0"
REGIONS_REFRESH_INTERVAL = timedelta(hours=24)
FIRE_REMOVAL_GRACE_PERIOD = timedelta(hours=24)

DEFAULT_OPTIONS = {
    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
    CONF_CREATE_REGION_SENSORS: True,
    CONF_CREATE_DEPARTMENT_SENSORS: True,
    CONF_CREATE_FIRE_GEOLOCATIONS: True,
    CONF_PROXIMITY_RADIUS_KM: DEFAULT_PROXIMITY_RADIUS_KM,
}

PLATFORMS = ["sensor", "binary_sensor", "geo_location"]
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_POLL_INTERVAL)

SERVICE_REFRESH = "refresh"
