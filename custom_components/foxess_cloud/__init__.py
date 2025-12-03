"""The FoxESS Cloud integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import voluptuous as vol

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .api_client import FoxESSCloudClient
from .api_client.models import InverterDetail, SchedulerGroup, SchedulerSetRequest
from .api_call_tracker import ApiCallTracker
from .coordinator import (
    FoxESSCloudDeviceDetailCoordinator,
    FoxESSCloudRealTimeCoordinator,
    FoxESSCloudSchedulerCoordinator,
)
from .const import CONF_API_KEY, CONF_DEVICE_SN, DOMAIN, PLATFORMS, SERVICE_SET_SCHEDULE


type FoxESSCloudConfigEntry = ConfigEntry["FoxESSCloudRuntimeData"]


_LOGGER = logging.getLogger(__name__)


@dataclass
class FoxESSCloudRuntimeData:
    """Runtime data stored on the config entry."""

    session: ClientSession
    client: FoxESSCloudClient
    api_call_tracker: ApiCallTracker
    device_detail_coordinator: FoxESSCloudDeviceDetailCoordinator
    device_info: DeviceInfo
    realtime_coordinator: FoxESSCloudRealTimeCoordinator
    scheduler_coordinator: FoxESSCloudSchedulerCoordinator | None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the FoxESS Cloud integration (register services)."""

    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FoxESSCloudConfigEntry) -> bool:
    """Set up FoxESS Cloud from a config entry."""

    api_call_tracker = ApiCallTracker()
    session = async_get_clientsession(hass)
    client = FoxESSCloudClient(
        api_key=entry.data[CONF_API_KEY],
        session=session,
        on_api_call=api_call_tracker.record_call,
    )
    device_detail_coordinator = FoxESSCloudDeviceDetailCoordinator(
        hass=hass,
        client=client,
        config_entry=entry,
    )
    realtime_coordinator = FoxESSCloudRealTimeCoordinator(
        hass=hass,
        client=client,
        config_entry=entry,
    )
    scheduler_coordinator: FoxESSCloudSchedulerCoordinator | None = None

    await device_detail_coordinator.async_config_entry_first_refresh()
    await realtime_coordinator.async_config_entry_first_refresh()

    device_info = _device_info_from_detail(
        entry=entry,
        detail=device_detail_coordinator.data,
    )

    has_scheduler = True
    if device_detail_coordinator.data and device_detail_coordinator.data.function is not None:
        has_scheduler = bool(device_detail_coordinator.data.function.get("scheduler"))

    if has_scheduler:
        scheduler_coordinator = FoxESSCloudSchedulerCoordinator(
            hass=hass,
            client=client,
            config_entry=entry,
        )
        await scheduler_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FoxESSCloudRuntimeData(
        session=session,
        client=client,
        api_call_tracker=api_call_tracker,
        device_detail_coordinator=device_detail_coordinator,
        device_info=device_info,
        realtime_coordinator=realtime_coordinator,
        scheduler_coordinator=scheduler_coordinator,
    )

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FoxESSCloudConfigEntry) -> bool:
    """Unload a FoxESS Cloud config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data = None

    return unload_ok


def _device_info_from_detail(
    *,
    entry: FoxESSCloudConfigEntry,
    detail: InverterDetail | None,
) -> DeviceInfo:
    """Build a DeviceInfo object from inverter detail data."""

    device_sn = entry.data[CONF_DEVICE_SN]
    name = entry.title or device_sn

    model: str | None = None
    sw_version: str | None = None
    hw_version: str | None = None

    if detail:
        model = detail.device_type or detail.product_type
        sw_version = detail.manager_version or detail.master_version or detail.slave_version
        hw_version = detail.hardware_version

    return DeviceInfo(
        identifiers={(DOMAIN, device_sn)},
        name=name,
        manufacturer="FoxESS",
        model=model,
        sw_version=sw_version,
        hw_version=hw_version,
        serial_number=device_sn,
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register integration level services once."""

    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def async_handle_set_schedule(call: service.ServiceCall) -> None:
        device_sn: str = call.data[CONF_DEVICE_SN]
        group_payloads = call.data["groups"]

        # Find matching config entry
        entry = next(
            (
                ent
                for ent in hass.config_entries.async_entries(DOMAIN)
                if ent.state is not None and ent.data.get(CONF_DEVICE_SN) == device_sn
            ),
            None,
        )
        if entry is None or entry.runtime_data is None:
            raise service.ServiceValidationError("Target inverter is not configured or not loaded")

        runtime: FoxESSCloudRuntimeData = entry.runtime_data

        if runtime.scheduler_coordinator is None:
            raise service.ServiceValidationError("Scheduler is not supported for this device")

        # Validate groups into SchedulerGroup models
        groups: list[SchedulerGroup] = []
        try:
            for payload in group_payloads:
                groups.append(SchedulerGroup.model_validate(payload))
        except Exception as err:  # noqa: BLE001
            raise service.ServiceValidationError("Invalid scheduler group payload") from err

        request = SchedulerSetRequest(device_sn=device_sn, groups=groups)

        await runtime.client.async_set_scheduler(request)
        await runtime.scheduler_coordinator.async_request_refresh()

    schema = vol.Schema(
        {
            vol.Required(CONF_DEVICE_SN): str,
            vol.Required("groups"): vol.All([dict]),
        }
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_handle_set_schedule,
        schema=schema,
    )
