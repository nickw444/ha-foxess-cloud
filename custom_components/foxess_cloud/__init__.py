"""The FoxESS Cloud integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import voluptuous as vol

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .api_call_tracker import ApiCallTracker
from .api_client import FoxESSCloudClient
from .api_client.models import InverterDetail, SchedulerGroup, SchedulerSetRequest
from .api_client.errors import FoxESSCloudApiError
from .const import (
    CONF_API_KEY,
    CONF_DEVICE_SN,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_FORCE_CHARGE,
    SERVICE_SET_FORCE_CHARGE,
    SERVICE_SET_SCHEDULE,
)
from .coordinator import (
    FoxESSCloudDeviceDetailCoordinator,
    FoxESSCloudRealTimeCoordinator,
    FoxESSCloudSchedulerCoordinator,
)
from .profiles import DeviceSeriesProfile, select_device_series_profile
from .scheduler_merge import (
    DEFAULT_MAX_GROUPS,
    FORCE_CHARGE_MODES,
    ForceChargeWindow,
    ScheduleMergeError,
    merge_force_charge,
    remove_force_charge,
)

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
    device_series_profile: DeviceSeriesProfile
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
    await device_detail_coordinator.async_config_entry_first_refresh()

    detail = device_detail_coordinator.data
    device_series_profile = select_device_series_profile(detail)
    product_type = detail.product_type if detail is not None else None
    device_type = detail.device_type if detail is not None else None
    _LOGGER.info(
        "Using device series profile %s for %s (product_type=%s, device_type=%s)",
        device_series_profile.profile_id,
        entry.data[CONF_DEVICE_SN],
        product_type,
        device_type,
    )
    realtime_coordinator = FoxESSCloudRealTimeCoordinator(
        hass=hass,
        client=client,
        config_entry=entry,
        variables=device_series_profile.realtime_variables(),
    )
    await realtime_coordinator.async_config_entry_first_refresh()

    device_info = _device_info_from_detail(
        entry=entry,
        detail=device_detail_coordinator.data,
    )

    scheduler_coordinator: FoxESSCloudSchedulerCoordinator | None = None
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
        device_series_profile=device_series_profile,
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


def _scheduler_runtime(hass: HomeAssistant, device_sn: str) -> FoxESSCloudRuntimeData:
    """Return runtime data for a loaded entry whose device supports the scheduler."""

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
    return runtime


async def _async_write_groups(
    runtime: FoxESSCloudRuntimeData, device_sn: str, groups: list[SchedulerGroup]
) -> None:
    """Write scheduler groups (overwrites the inverter schedule) and refresh."""

    request = SchedulerSetRequest(device_sn=device_sn, groups=groups)
    await runtime.client.async_set_scheduler(request)
    if runtime.scheduler_coordinator is not None:
        await runtime.scheduler_coordinator.async_request_refresh()


def _register_services(hass: HomeAssistant) -> None:
    """Register integration level services once."""

    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def async_handle_set_schedule(call: service.ServiceCall) -> None:
        device_sn: str = call.data[CONF_DEVICE_SN]
        group_payloads = call.data["groups"]
        runtime = _scheduler_runtime(hass, device_sn)

        # Validate groups into SchedulerGroup models
        groups: list[SchedulerGroup] = []
        try:
            for payload in group_payloads:
                groups.append(SchedulerGroup.model_validate(payload))
        except Exception as err:  # noqa: BLE001
            raise service.ServiceValidationError("Invalid scheduler group payload") from err

        await _async_write_groups(runtime, device_sn, groups)

    async def async_handle_set_force_charge(call: service.ServiceCall) -> None:
        """Add/replace a force-charge window while keeping all other enabled groups."""

        device_sn: str = call.data[CONF_DEVICE_SN]
        runtime = _scheduler_runtime(hass, device_sn)

        # Always read the live schedule so we never merge into stale data.
        try:
            current = await runtime.client.async_get_scheduler(device_sn)
        except FoxESSCloudApiError as err:
            raise service.ServiceValidationError("Could not read the current schedule") from err

        min_soc_on_grid = call.data.get("min_soc_on_grid")
        if min_soc_on_grid is None:
            min_soc_on_grid = next(
                (g.min_soc_on_grid for g in current.groups if g.enable == 1 and g.work_mode == "SelfUse"),
                10,
            )

        window = ForceChargeWindow(
            start=call.data["start_time"],
            end=call.data["end_time"],
            target_soc=call.data["target_soc"],
            power=call.data["power"],
            min_soc_on_grid=min_soc_on_grid,
            max_soc=call.data["max_soc"],
            work_mode=call.data["work_mode"],
        )
        try:
            groups = merge_force_charge(current.groups, window, max_groups=max(len(current.groups), DEFAULT_MAX_GROUPS))
        except ScheduleMergeError as err:
            raise service.ServiceValidationError(str(err)) from err

        await _async_write_groups(runtime, device_sn, groups)

    async def async_handle_clear_force_charge(call: service.ServiceCall) -> None:
        """Remove force-charge windows while keeping all other enabled groups."""

        device_sn: str = call.data[CONF_DEVICE_SN]
        runtime = _scheduler_runtime(hass, device_sn)
        try:
            current = await runtime.client.async_get_scheduler(device_sn)
        except FoxESSCloudApiError as err:
            raise service.ServiceValidationError("Could not read the current schedule") from err

        await _async_write_groups(runtime, device_sn, remove_force_charge(current.groups))

    schema = vol.Schema(
        {
            vol.Required(CONF_DEVICE_SN): str,
            vol.Required("groups"): vol.All([dict]),
        }
    )
    force_charge_schema = vol.Schema(
        {
            vol.Required(CONF_DEVICE_SN): str,
            vol.Required("start_time"): cv.time,
            vol.Required("end_time"): cv.time,
            vol.Required("target_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Required("power"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("min_soc_on_grid"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Optional("max_soc", default=100): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Optional("work_mode", default="ForceCharge"): vol.In(sorted(FORCE_CHARGE_MODES)),
        }
    )
    clear_schema = vol.Schema({vol.Required(CONF_DEVICE_SN): str})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_handle_set_schedule,
        schema=schema,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FORCE_CHARGE,
        async_handle_set_force_charge,
        schema=force_charge_schema,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_FORCE_CHARGE,
        async_handle_clear_force_charge,
        schema=clear_schema,
    )
