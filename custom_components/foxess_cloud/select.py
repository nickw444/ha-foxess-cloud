"""Select platform for FoxESS schedule work mode staging."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import FoxESSCloudSchedulerCoordinator
from .api_client import FoxESSCloudClient

WORK_MODES = [
    "SelfUse",
    "Feedin",
    "Backup",
    "PeakShaving",
]

SCAN_INTERVAL = timedelta(minutes=15)


class FoxESSWorkModeSelect(SelectEntity):
    """Select entity to read and set inverter work mode (WorkMode setting)."""

    _attr_has_entity_name = True
    _attr_translation_key = "work_mode"
    _attr_options = WORK_MODES
    _attr_entity_registry_enabled_default = True
    _attr_should_poll = True
    _attr_scan_interval = SCAN_INTERVAL

    def __init__(
        self,
        *,
        client: FoxESSCloudClient,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        self._client = client
        self._device_sn = device_sn
        self._attr_unique_id = f"{device_sn}_work_mode"
        self._attr_device_info = device_info

    @property
    def scan_interval(self) -> timedelta:
        # Explicit property to ensure Home Assistant respects 15-minute polling.
        return SCAN_INTERVAL

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option

    async def async_update(self) -> None:
        setting = await self._client.async_get_setting(self._device_sn, "WorkMode")
        value = setting.value
        if isinstance(value, str) and value in WORK_MODES:
            self._attr_current_option = value
        else:
            self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        if option not in WORK_MODES:
            raise ValueError(f"Unsupported work mode: {option}")
        await self._client.async_set_setting(self._device_sn, "WorkMode", option)
        self._attr_current_option = option

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "notice": (
                "Changing work mode fails with error 44096 when a scheduler is active; "
                "disable schedule first if you see 'Unsupported function code'."
            )
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up work mode select for schedule staging."""

    runtime = entry.runtime_data
    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = runtime.device_info

    entities: list[SelectEntity] = []

    entities.append(
        FoxESSWorkModeSelect(
            client=entry.runtime_data.client,
            device_sn=device_sn,
            device_info=device_info,
        )
    )

    if runtime.scheduler_coordinator is not None:
        entities.append(
            FoxESSScheduleWorkModeSelect(
                device_sn=device_sn,
                device_info=device_info,
                coordinator=runtime.scheduler_coordinator,
            )
        )

    async_add_entities(entities)


class FoxESSScheduleWorkModeSelect(CoordinatorEntity[FoxESSCloudSchedulerCoordinator], SelectEntity):
    """Select for staging scheduler work mode."""

    _attr_has_entity_name = True
    _attr_options = WORK_MODES
    _attr_translation_key = "schedule_work_mode"

    def __init__(
        self,
        device_sn: str,
        device_info: DeviceInfo,
        coordinator,
    ) -> None:
        self._device_sn = device_sn
        self._attr_unique_id = f"{device_sn}_scheduler_work_mode"
        self._attr_entity_registry_enabled_default = True
        self._attr_device_info = device_info
        super().__init__(coordinator)

    @property
    def current_option(self) -> str | None:
        staging = self.coordinator.data
        if staging and staging.groups:
            return staging.groups[0].work_mode
        return None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.update_group(work_mode=option)
        self.async_write_ha_state()
