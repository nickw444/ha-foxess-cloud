"""Select platform for FoxESS schedule work mode staging."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import FoxESSCloudSchedulerCoordinator

WORK_MODES = [
    "SelfUse",
    "Feedin",
    "Backup",
    "ForceCharge",
    "ForceDischarge",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up work mode select for schedule staging."""

    runtime = entry.runtime_data
    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = runtime.device_info

    if runtime.scheduler_coordinator is None:
        return

    entities = [
        FoxESSScheduleWorkModeSelect(
            device_sn=device_sn,
            device_info=device_info,
            coordinator=runtime.scheduler_coordinator,
        )
    ]

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
