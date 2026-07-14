"""Config flow for Feux de Foret."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_CREATE_DEPARTMENT_SENSORS,
    CONF_CREATE_FIRE_GEOLOCATIONS,
    CONF_CREATE_REGION_SENSORS,
    CONF_POLL_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
    MIN_POLL_INTERVAL,
    NAME,
)


class FeuxDeForetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Feux de Foret."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            options = {
                key: user_input[key] for key in DEFAULT_OPTIONS if key in user_input
            }
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, NAME),
                data={CONF_NAME: user_input.get(CONF_NAME, NAME)},
                options=options,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_options_schema({CONF_NAME: NAME, **DEFAULT_OPTIONS}),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FeuxDeForetOptionsFlow(config_entry)


class FeuxDeForetOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Feux de Foret."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**DEFAULT_OPTIONS, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current, include_name=False),
        )


def _options_schema(
    defaults: dict[str, Any], *, include_name: bool = True
) -> vol.Schema:
    """Return the shared setup/options schema."""
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, NAME))] = str
    fields.update(
        {
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(
                    CONF_POLL_INTERVAL, DEFAULT_OPTIONS[CONF_POLL_INTERVAL]
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL)),
            vol.Required(
                CONF_CREATE_REGION_SENSORS,
                default=defaults.get(CONF_CREATE_REGION_SENSORS, True),
            ): bool,
            vol.Required(
                CONF_CREATE_DEPARTMENT_SENSORS,
                default=defaults.get(CONF_CREATE_DEPARTMENT_SENSORS, True),
            ): bool,
            vol.Required(
                CONF_CREATE_FIRE_GEOLOCATIONS,
                default=defaults.get(CONF_CREATE_FIRE_GEOLOCATIONS, True),
            ): bool,
        }
    )
    return vol.Schema(fields)
