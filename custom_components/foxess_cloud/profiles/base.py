"""Device series profiles.

A profile encapsulates all series-specific logic (e.g. variable names and entity sets)
so the rest of the integration can remain series-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..coordinator import FoxESSCloudRealTimeCoordinator


class DeviceSeriesProfile(ABC):
    """Base class for series-specific behavior."""

    profile_id: str

    def realtime_variables(self) -> list[str] | None:
        """Return variables to request from the realtime endpoint.

        Returning `None` requests all variables (recommended unless you have a strong
        reason to limit the payload).
        """

        return None

    @abstractmethod
    async def async_setup_entry_sensor(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        *,
        device_sn: str,
        device_info: DeviceInfo,
        coordinator: FoxESSCloudRealTimeCoordinator,
    ) -> None:
        """Set up sensor entities for this device series."""

