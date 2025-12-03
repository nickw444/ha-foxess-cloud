"""Number platform for FoxESS Cloud device settings."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_client import FoxESSCloudClient
from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import FoxESSCloudSchedulerCoordinator

SCAN_INTERVAL = timedelta(hours=1)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FoxESS Cloud numbers from a config entry."""

    client: FoxESSCloudClient = entry.runtime_data.client

    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = entry.runtime_data.device_info

    setting_entities = [
        FoxESSSettingNumber(
            client=client,
            device_sn=device_sn,
            device_info=device_info,
            setting_key="ExportLimit",
            translation_key="export_limit",
            native_unit_of_measurement=None,
            native_min_value=0,
            native_max_value=30000,
            icon="mdi:export-variant",
        ),
        FoxESSSettingNumber(
            client=client,
            device_sn=device_sn,
            device_info=device_info,
            setting_key="MinSoc",
            translation_key="min_soc",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-arrow-down",
        ),
        FoxESSSettingNumber(
            client=client,
            device_sn=device_sn,
            device_info=device_info,
            setting_key="MinSocOnGrid",
            translation_key="min_soc_on_grid",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-arrow-down-outline",
        ),
        FoxESSSettingNumber(
            client=client,
            device_sn=device_sn,
            device_info=device_info,
            setting_key="MaxSoc",
            translation_key="max_soc",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-arrow-up",
        ),
    ]

    # Scheduler numbers (single schedule)
    coord: FoxESSCloudSchedulerCoordinator = entry.runtime_data.scheduler_coordinator
    scheduler_entities = [
        FoxESSScheduleNumber(
            coordinator=coord,
            device_sn=device_sn,
            device_info=device_info,
            key="min_soc_on_grid",
            translation_key="scheduler_min_soc_on_grid",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-arrow-down-outline",
            enabled_default=True,
        ),
        FoxESSScheduleNumber(
            coordinator=coord,
            device_sn=device_sn,
            device_info=device_info,
            key="fd_soc",
            translation_key="scheduler_fd_soc",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-arrow-up-outline",
            enabled_default=True,
        ),
        FoxESSScheduleNumber(
            coordinator=coord,
            device_sn=device_sn,
            device_info=device_info,
            key="fd_pwr",
            translation_key="scheduler_fd_pwr",
            native_unit_of_measurement="W",
            native_min_value=0,
            native_max_value=30000,
            icon="mdi:flash",
            enabled_default=True,
        ),
        FoxESSScheduleNumber(
            coordinator=coord,
            device_sn=device_sn,
            device_info=device_info,
            key="max_soc",
            translation_key="scheduler_max_soc",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            icon="mdi:battery-high",
            enabled_default=True,
        ),
    ]

    # Polling entities: let SCAN_INTERVAL drive regular updates; initial fetch is handled in async_added_to_hass.
    async_add_entities(setting_entities)
    # Coordinator-backed scheduler numbers rely on coordinator refreshes; no extra pre-add fetch.
    async_add_entities(scheduler_entities)


class FoxESSSettingNumber(NumberEntity):
    """Number entity for a writable FoxESS setting with self-managed I/O."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_entity_registry_enabled_default = False
    _attr_scan_interval = SCAN_INTERVAL

    def __init__(
        self,
        client: FoxESSCloudClient,
        device_sn: str,
        device_info: DeviceInfo,
        *,
        setting_key: str,
        translation_key: str,
        native_unit_of_measurement: str | None,
        native_min_value: float | None = None,
        native_max_value: float | None = None,
        icon: str | None = None,
    ) -> None:
        self._client = client
        self._device_sn = device_sn
        self._setting_key = setting_key
        self._attr_unique_id = f"{device_sn}_{setting_key.lower()}"
        self._attr_translation_key = translation_key
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_info = device_info
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_icon = icon
        self._cached_value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._cached_value

    async def async_set_native_value(self, value: float) -> None:
        await self._client.async_set_setting(self._device_sn, self._setting_key, value)
        self._cached_value = value

    async def async_added_to_hass(self) -> None:
        """Run when entity is added; prime state for enabled entities only."""

        await super().async_added_to_hass()

        if self.registry_entry and self.registry_entry.disabled_by is not None:
            self._LOGGER.debug(
                "Skipping initial update for disabled setting entity %s", self._attr_unique_id
            )
            return

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        """Fetch the setting directly (interval governed by SCAN_INTERVAL)."""

        setting = await self._client.async_get_setting(self._device_sn, self._setting_key)
        try:
            self._cached_value = float(setting.value) if setting.value is not None else None
        except (TypeError, ValueError):
            self._cached_value = None


class FoxESSScheduleNumber(CoordinatorEntity[FoxESSCloudSchedulerCoordinator], NumberEntity):
    """Number entity for scheduler parameters."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxESSCloudSchedulerCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
        key: str,
        translation_key: str,
        native_unit_of_measurement: str | None,
        native_min_value: float,
        native_max_value: float,
        icon: str | None = None,
        enabled_default: bool = False,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{device_sn}_scheduler_{key.lower()}"
        self._attr_translation_key = translation_key
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled_default

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or not data.groups:
            return None
        g = data.groups[0]
        value = getattr(g, self._key, None)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.update_group(**{self._key: value})
        self.async_write_ha_state()
