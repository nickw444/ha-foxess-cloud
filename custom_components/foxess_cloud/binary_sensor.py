"""Binary sensor platform for FoxESS Cloud scheduler and faults."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import (
    FoxESSCloudDeviceDetailCoordinator,
    FoxESSCloudRealTimeCoordinator,
    FoxESSCloudSchedulerCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FoxESS Cloud binary sensors from a config entry."""

    scheduler: FoxESSCloudSchedulerCoordinator | None = entry.runtime_data.scheduler_coordinator
    realtime: FoxESSCloudRealTimeCoordinator = entry.runtime_data.realtime_coordinator
    detail: FoxESSCloudDeviceDetailCoordinator = entry.runtime_data.device_detail_coordinator

    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = entry.runtime_data.device_info

    async_add_entities(
        [
            FoxESSCurrentFaultBinarySensor(
                coordinator=realtime,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSHasBatteryBinarySensor(
                coordinator=detail,
                device_sn=device_sn,
                device_info=device_info,
            ),
        ]
    )

    if scheduler is None:
        return

    async_add_entities(
        [
            FoxESSSchedulerEnabledBinarySensor(
                coordinator=scheduler,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSScheduleDirtyBinarySensor(
                coordinator=scheduler,
                device_sn=device_sn,
                device_info=device_info,
            ),
        ]
    )


class FoxESSSchedulerEnabledBinarySensor(
    CoordinatorEntity[FoxESSCloudSchedulerCoordinator], BinarySensorEntity
):
    """Binary sensor indicating if a scheduler is enabled."""

    _attr_has_entity_name = True
    _attr_translation_key = "scheduler_enabled"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:clock-outline"
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: FoxESSCloudSchedulerCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_scheduler_enabled"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if scheduler is enabled."""
        data = self.coordinator.last_scheduler or self.coordinator.data
        if data is None:
            return None
        return bool(data.enable)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return raw scheduler data as attributes."""

        data = self.coordinator.last_scheduler or self.coordinator.data
        if data is None:
            return None

        return {
            "enable": data.enable,
            "groups": [group.model_dump() for group in data.groups],
        }


class FoxESSScheduleDirtyBinarySensor(
    CoordinatorEntity[FoxESSCloudSchedulerCoordinator], BinarySensorEntity
):
    """Binary sensor indicating staged/unsaved scheduler changes."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:circle-edit-outline"
    _attr_translation_key = "schedule_dirty"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: FoxESSCloudSchedulerCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_scheduler_dirty"
        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = True

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.is_dirty()


class FoxESSCurrentFaultBinarySensor(
    CoordinatorEntity[FoxESSCloudRealTimeCoordinator], BinarySensorEntity
):
    """Binary sensor indicating whether a current fault is active."""

    _attr_has_entity_name = True
    _attr_translation_key = "current_fault"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxESSCloudRealTimeCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_current_fault"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if a fault code is present and non-zero."""

        data = self.coordinator.data
        if data is None:
            return None
        fault = getattr(data, "currentFault", None)
        code = getattr(fault, "value", None)
        if code is None:
            return False
        try:
            return float(code) != 0
        except (TypeError, ValueError):
            return bool(code)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return raw fault info."""

        data = self.coordinator.data
        if data is None:
            return None
        fault = getattr(data, "currentFault", None)
        count = getattr(data, "currentFaultCount", None)
        attributes = {}
        if fault and getattr(fault, "value", None) is not None:
            attributes["code"] = fault.value
        if count and getattr(count, "value", None) is not None:
            attributes["count"] = count.value
        return attributes or None


class FoxESSHasBatteryBinarySensor(
    CoordinatorEntity[FoxESSCloudDeviceDetailCoordinator], BinarySensorEntity
):
    """Binary sensor reflecting whether the inverter reports a battery."""

    _attr_has_entity_name = True
    _attr_translation_key = "has_battery"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxESSCloudDeviceDetailCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_has_battery"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        detail = self.coordinator.data
        if detail is None or detail.has_battery is None:
            return None
        return bool(detail.has_battery)
