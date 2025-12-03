"""Switch platform for FoxESS Cloud scheduler enable."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import FoxESSCloudSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up schedule enable switches."""

    scheduler_coordinator: FoxESSCloudSchedulerCoordinator | None = entry.runtime_data.scheduler_coordinator
    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = entry.runtime_data.device_info

    if scheduler_coordinator is None:
        return

    entities = [FoxESSScheduleEnableSwitch(scheduler_coordinator, device_sn, device_info)]
    async_add_entities(entities)


class FoxESSScheduleEnableSwitch(CoordinatorEntity[FoxESSCloudSchedulerCoordinator], SwitchEntity):
    """Switch to enable/disable the staged scheduler group."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "scheduler_enable"

    def __init__(
        self,
        coordinator: FoxESSCloudSchedulerCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        self._attr_unique_id = f"{device_sn}_scheduler_enable"
        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = True
        super().__init__(coordinator)

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        if data and data.groups:
            return bool(data.groups[0].enable)
        return False

    async def async_turn_on(self, **kwargs):
        self.coordinator.update_group(enable=1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self.coordinator.update_group(enable=0)
        self.async_write_ha_state()
