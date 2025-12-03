"""Button platform for FoxESS schedule override."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import (
    FoxESSCloudRealTimeCoordinator,
    FoxESSCloudSchedulerCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up schedule override button."""

    runtime = entry.runtime_data
    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = runtime.device_info

    async_add_entities(
        [
            FoxESSRealTimeRefreshButton(
                coordinator=runtime.realtime_coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
        ]
    )

    if runtime.scheduler_coordinator is not None:
        async_add_entities(
            [
                FoxESSScheduleOverrideButton(
                    runtime_data=runtime,
                    device_sn=device_sn,
                    device_info=device_info,
                ),
                FoxESSScheduleRestoreButton(
                    coordinator=runtime.scheduler_coordinator,
                    device_sn=device_sn,
                    device_info=device_info,
                ),
            ]
        )


class FoxESSRealTimeRefreshButton(CoordinatorEntity[FoxESSCloudRealTimeCoordinator], ButtonEntity):
    """Button to trigger an immediate realtime data refresh."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"
    _attr_translation_key = "refresh_realtime"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        *,
        coordinator: FoxESSCloudRealTimeCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_refresh_realtime"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class FoxESSScheduleOverrideButton(CoordinatorEntity[FoxESSCloudSchedulerCoordinator], ButtonEntity):
    """Button to push staged schedule to the inverter."""

    _attr_has_entity_name = True
    _attr_translation_key = "override_schedule"
    _attr_icon = "mdi:clock-check"

    def __init__(self, runtime_data, device_sn: str, device_info: DeviceInfo) -> None:
        super().__init__(runtime_data.scheduler_coordinator)
        self._runtime_data = runtime_data
        self._device_sn = device_sn
        self._attr_unique_id = f"{device_sn}_override_schedule"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        try:
            await self._runtime_data.scheduler_coordinator.async_submit_group()
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Failed to set schedule: {err}") from err

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self._runtime_data.scheduler_coordinator.data
        if not data:
            return None
        return {
            "staged": [group.model_dump() for group in data.groups],
            "staged_enable": data.enable,
        }


class FoxESSScheduleRestoreButton(ButtonEntity):
    """Button to restore staged scheduler values from the last fetch."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:backup-restore"
    _attr_translation_key = "restore_scheduler"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{device_sn}_scheduler_restore"
        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = True

    async def async_press(self) -> None:
        self._coordinator.restore_staged_group()
