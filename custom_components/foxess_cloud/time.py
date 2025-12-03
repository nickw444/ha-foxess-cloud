"""Time platform for the FoxESS Cloud scheduler group."""

from __future__ import annotations

from datetime import time
from typing import Literal

from homeassistant.components.time import TimeEntity
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
    """Set up schedule time entities."""

    scheduler_coordinator: FoxESSCloudSchedulerCoordinator | None = entry.runtime_data.scheduler_coordinator
    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = entry.runtime_data.device_info

    if scheduler_coordinator is None:
        return

    entities = [
        FoxESSScheduleTimeEntity(
            coordinator=scheduler_coordinator,
            device_sn=device_sn,
            device_info=device_info,
            kind="start",
        ),
        FoxESSScheduleTimeEntity(
            coordinator=scheduler_coordinator,
            device_sn=device_sn,
            device_info=device_info,
            kind="end",
        ),
    ]

    async_add_entities(entities)


class FoxESSScheduleTimeEntity(CoordinatorEntity[FoxESSCloudSchedulerCoordinator], TimeEntity):
    """Time entity for scheduler start/end."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: FoxESSCloudSchedulerCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
        kind: Literal["start", "end"],
    ) -> None:
        self._kind = kind
        self._attr_unique_id = f"{device_sn}_scheduler_{kind}_time"
        self._attr_translation_key = f"scheduler_{kind}_time"
        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = True
        super().__init__(coordinator)

    @property
    def native_value(self) -> time | None:
        data = self.coordinator.data
        if not data or not data.groups:
            return None
        g = data.groups[0]
        hour = g.start_hour if self._kind == "start" else g.end_hour
        minute = g.start_minute if self._kind == "start" else g.end_minute
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time | str) -> None:
        if isinstance(value, str):
            hour, minute = map(int, value.split(":"))
        else:
            hour, minute = value.hour, value.minute

        if self._kind == "start":
            self.coordinator.update_group(start_hour=hour, start_minute=minute)
        else:
            self.coordinator.update_group(end_hour=hour, end_minute=minute)
        self.async_write_ha_state()
