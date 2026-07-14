"""Integration tests for the Home Assistant config and options flows."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.feuxdeforet_fr.const import (
    CONF_PROXIMITY_RADIUS_KM,
    DEFAULT_OPTIONS,
    DOMAIN,
    NAME,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_user_form_loads(hass: HomeAssistant) -> None:
    """The initial setup form must load without contacting the API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    schema_keys = {key.schema for key in result["data_schema"].schema}
    assert CONF_PROXIMITY_RADIUS_KM in schema_keys


async def test_options_flow_loads_and_saves(hass: HomeAssistant) -> None:
    """The gear-button flow must load and persist updated options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        title=NAME,
        data={CONF_NAME: NAME},
        options=DEFAULT_OPTIONS,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    options = {**DEFAULT_OPTIONS, CONF_PROXIMITY_RADIUS_KM: 15.0}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=options
    )

    assert result["type"] == "create_entry"
    assert result["data"] == options
