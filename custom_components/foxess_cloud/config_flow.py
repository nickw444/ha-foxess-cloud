"""Config flow for the FoxESS Cloud integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithReload
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import (
    FoxESSCloudApiError,
    FoxESSCloudAuthError,
    FoxESSCloudClient,
    FoxESSCloudConnectionError,
)
from .api_client.models import Inverter
from .const import (
    CONF_API_KEY,
    CONF_DEVICE_SN,
    CONF_REALTIME_UPDATE_INTERVAL,
    DEFAULT_REALTIME_UPDATE_INTERVAL,
    MAX_REALTIME_UPDATE_INTERVAL,
    MIN_REALTIME_UPDATE_INTERVAL,
    DOMAIN,
)


class CannotConnect(Exception):
    """Error to indicate the connection could not be established."""


class InvalidAuth(Exception):
    """Error to indicate invalid authentication."""


class FoxESSCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FoxESS Cloud."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Return the options flow handler."""

        return FoxESSCloudOptionsFlow()

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._api_key: str | None = None
        self._devices: list[Inverter] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step where the user provides credentials."""

        errors: dict[str, str] = {}

        if user_input is None:
            return self._async_show_user_form(errors)

        api_key = user_input[CONF_API_KEY].strip()

        try:
            devices = await self._async_fetch_devices(self.hass, api_key)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001 - broad by design in config flows
            errors["base"] = "unknown"
        else:
            if not devices:
                errors["base"] = "no_devices"

        if errors:
            return self._async_show_user_form(errors, user_input)

        self._api_key = api_key
        self._devices = devices

        return await self.async_step_select_device()

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which device to set up."""

        if self._api_key is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}

        if self._devices is None:
            try:
                self._devices = await self._async_fetch_devices(self.hass, self._api_key)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - defensive guard
                errors["base"] = "unknown"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"

            if errors:
                return self._async_show_user_form(errors)

        device_map = {
            device.device_sn: f"{device.station_name or 'FoxESS device'} - {device.device_sn}"
            for device in self._devices or []
        }

        if user_input:
            device_sn = user_input[CONF_DEVICE_SN]

            if device_sn not in device_map:
                errors["base"] = "unknown_device"
            else:
                await self.async_set_unique_id(device_sn.lower())
                self._abort_if_unique_id_configured()

                selected = next(
                    (device for device in self._devices or [] if device.device_sn == device_sn),
                    None,
                )

                title = selected.station_name if selected and selected.station_name else device_sn

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_DEVICE_SN: device_sn,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_SN): vol.In(device_map),
            }
        )

        return self.async_show_form(
            step_id="select_device", data_schema=data_schema, errors=errors
        )

    def _async_show_user_form(
        self, errors: dict[str, str], user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the user step form."""

        defaults = user_input or {}

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def _async_fetch_devices(
        self, hass: HomeAssistant, api_key: str
    ) -> list[Inverter]:
        """Fetch all devices available for the account."""

        if not api_key:
            raise InvalidAuth

        session = async_get_clientsession(hass)
        client = FoxESSCloudClient(api_key=api_key, session=session)

        try:
            return await client.async_list_inverters(page=1, page_size=20)
        except FoxESSCloudAuthError as err:
            raise InvalidAuth from err
        except (FoxESSCloudConnectionError, FoxESSCloudApiError) as err:
            raise CannotConnect from err


class FoxESSCloudOptionsFlow(OptionsFlowWithReload):
    """Handle FoxESS Cloud configuration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage FoxESS Cloud options."""

        if user_input is not None:
            interval = int(user_input[CONF_REALTIME_UPDATE_INTERVAL])
            interval = max(MIN_REALTIME_UPDATE_INTERVAL, interval)
            interval = min(MAX_REALTIME_UPDATE_INTERVAL, interval)

            return self.async_create_entry(
                title="",
                data={CONF_REALTIME_UPDATE_INTERVAL: interval},
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_REALTIME_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_REALTIME_UPDATE_INTERVAL, DEFAULT_REALTIME_UPDATE_INTERVAL
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_REALTIME_UPDATE_INTERVAL,
                        max=MAX_REALTIME_UPDATE_INTERVAL,
                        step=1,
                        unit_of_measurement="min",
                        mode="box",
                    )
                )
            }
        )

        data_schema = self.add_suggested_values_to_schema(
            data_schema, self.config_entry.options
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
