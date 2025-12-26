"""Update coordinator for FoxESS Cloud devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import FoxESSCloudApiError, FoxESSCloudClient, FoxESSCloudConnectionError
from .api_client.errors import FoxESSCloudAuthError
from .api_client.models import (
    InverterDetail,
    RealTimeSnapshot,
    SchedulerGroup,
    SchedulerInfo,
    SchedulerSetRequest,
)
from .const import (
    CONF_DEVICE_SN,
    CONF_REALTIME_UPDATE_INTERVAL,
    DEFAULT_REALTIME_UPDATE_INTERVAL,
    DOMAIN,
    MAX_REALTIME_UPDATE_INTERVAL,
    MIN_REALTIME_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_DETAIL_UPDATE_INTERVAL = timedelta(hours=12)


class FoxESSCloudRealTimeCoordinator(DataUpdateCoordinator[RealTimeSnapshot]):
    """Coordinator to fetch real-time data for a single device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FoxESSCloudClient,
        config_entry: ConfigEntry,
        *,
        variables: list[str] | None = None,
    ) -> None:
        """Initialize the coordinator."""

        self._client = client
        self._device_sn: str = config_entry.data[CONF_DEVICE_SN]
        self._variables = variables

        update_interval_minutes = self._validated_update_interval(
            config_entry.options.get(
                CONF_REALTIME_UPDATE_INTERVAL, DEFAULT_REALTIME_UPDATE_INTERVAL
            )
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{self._device_sn}",
            update_interval=timedelta(minutes=update_interval_minutes),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> RealTimeSnapshot:
        """Fetch the latest real-time snapshot for the device."""

        try:
            return await self._client.async_get_real_time_snapshot(
                sn=self._device_sn,
                variables=self._variables,
            )
        except FoxESSCloudAuthError as err:
            raise UpdateFailed("Authentication failed while updating FoxESS Cloud data") from err
        except (FoxESSCloudConnectionError, FoxESSCloudApiError) as err:
            raise UpdateFailed("Error communicating with FoxESS Cloud") from err

    def _validated_update_interval(self, value: int | float) -> int:
        """Clamp user-provided interval (minutes) to supported bounds."""

        coerced = int(value)
        if coerced < MIN_REALTIME_UPDATE_INTERVAL:
            return MIN_REALTIME_UPDATE_INTERVAL
        if coerced > MAX_REALTIME_UPDATE_INTERVAL:
            return MAX_REALTIME_UPDATE_INTERVAL
        return coerced


class FoxESSCloudDeviceDetailCoordinator(DataUpdateCoordinator[InverterDetail]):
    """Coordinator to fetch semi-static device details."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FoxESSCloudClient,
        config_entry: ConfigEntry,
    ) -> None:
        self._client = client
        self._device_sn = config_entry.data[CONF_DEVICE_SN]

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_detail_{self._device_sn}",
            update_interval=DEVICE_DETAIL_UPDATE_INTERVAL,
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> InverterDetail:
        try:
            return await self._client.async_get_device_detail(self._device_sn)
        except FoxESSCloudAuthError as err:
            raise UpdateFailed("Authentication failed while fetching FoxESS Cloud device detail") from err
        except (FoxESSCloudConnectionError, FoxESSCloudApiError) as err:
            raise UpdateFailed("Error communicating with FoxESS Cloud device detail") from err


class FoxESSCloudSchedulerCoordinator(DataUpdateCoordinator[SchedulerInfo]):
    """Coordinator to fetch scheduler info for a device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FoxESSCloudClient,
        config_entry: ConfigEntry,
    ) -> None:
        self._client = client
        self._device_sn = config_entry.data[CONF_DEVICE_SN]
        self.staging: SchedulerGroup = self._default_group()
        self._dirty: bool = False
        self._last_scheduler: SchedulerInfo | None = None

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_scheduler_{self._device_sn}",
            update_interval=timedelta(hours=1),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> SchedulerInfo:
        try:
            data = await self._client.async_get_scheduler(self._device_sn)
        except FoxESSCloudAuthError as err:
            raise UpdateFailed("Authentication failed while fetching scheduler") from err
        except (FoxESSCloudConnectionError, FoxESSCloudApiError) as err:
            raise UpdateFailed("Error communicating with FoxESS Cloud scheduler") from err

        if not self._dirty:
            if data.groups:
                self.staging = data.groups[0]
            else:
                self.staging = self._default_group()
        self._last_scheduler = data.model_copy(deep=True)
        staged_info = self._staging_to_scheduler_info()
        return staged_info

    def update_group(
        self,
        *,
        enable: int | None = None,
        start_hour: int | None = None,
        start_minute: int | None = None,
        end_hour: int | None = None,
        end_minute: int | None = None,
        work_mode: str | None = None,
        min_soc_on_grid: int | None = None,
        fd_soc: int | None = None,
        fd_pwr: float | None = None,
        max_soc: int | None = None,
    ) -> None:
        """Update staged scheduler group values with typed fields."""

        updated = self.staging.model_copy(deep=True)

        if enable is not None:
            updated.enable = enable
        if (start_hour is None) ^ (start_minute is None):
            raise ValueError("start_hour and start_minute must be provided together")
        if (end_hour is None) ^ (end_minute is None):
            raise ValueError("end_hour and end_minute must be provided together")

        if start_hour is not None and start_minute is not None:
            updated.start_hour = start_hour
            updated.start_minute = start_minute
        if end_hour is not None and end_minute is not None:
            updated.end_hour = end_hour
            updated.end_minute = end_minute
        if work_mode is not None:
            updated.work_mode = work_mode
        if min_soc_on_grid is not None:
            updated.min_soc_on_grid = min_soc_on_grid
        if fd_soc is not None:
            updated.fd_soc = fd_soc
        if fd_pwr is not None:
            updated.fd_pwr = fd_pwr
        if max_soc is not None:
            updated.max_soc = max_soc

        _LOGGER.debug("Updating scheduler group with %s", updated)
        self.staging = updated
        self._dirty = True
        self.async_set_updated_data(self._staging_to_scheduler_info())

    async def async_submit_group(self) -> None:
        """Push the staged scheduler group to the API and refresh."""

        _LOGGER.debug("Submitting staged scheduler group: %s", self.staging)
        req = SchedulerSetRequest(device_sn=self._device_sn, groups=[self.staging])
        await self._client.async_set_scheduler(req)
        self._dirty = False
        await self.async_request_refresh()

    def restore_staged_group(self) -> None:
        """Restore staged values from the last fetched scheduler data or defaults."""

        if self._last_scheduler and self._last_scheduler.groups:
            self.staging = self._last_scheduler.groups[0].model_copy()
        else:
            self.staging = self._default_group()

        self._dirty = False
        self.async_set_updated_data(self._staging_to_scheduler_info())

    def is_dirty(self) -> bool:
        """Return True if the staged group has local changes."""

        return bool(self._dirty)

    def _staging_to_scheduler_info(self) -> SchedulerInfo:
        """Convert staged groups to SchedulerInfo for consumers."""

        enable = self._last_scheduler.enable if self._last_scheduler else 1
        return SchedulerInfo(enable=enable, groups=[self.staging])

    @property
    def last_scheduler(self) -> SchedulerInfo | None:
        """Return the last scheduler fetched from the API (raw)."""

        return self._last_scheduler

    def _default_group(self) -> SchedulerGroup:
        return SchedulerGroup(
            enable=0,
            startHour=0,
            startMinute=0,
            endHour=0,
            endMinute=0,
            workMode="SelfUse",
            minSocOnGrid=20,
            fdSoc=20,
            fdPwr=10000,
            maxSoc=100,
        )
