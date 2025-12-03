"""Constants for the FoxESS Cloud integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform


DOMAIN: Final = "foxess_cloud"
PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.TIME,
]

SERVICE_SET_SCHEDULE: Final = "set_schedule"

CONF_API_KEY: Final = "api_key"
CONF_DEVICE_SN: Final = "device_sn"
CONF_REALTIME_UPDATE_INTERVAL: Final = "realtime_update_interval"

DEFAULT_REALTIME_UPDATE_INTERVAL: Final = 5  # minutes
MIN_REALTIME_UPDATE_INTERVAL: Final = 1  # minutes
MAX_REALTIME_UPDATE_INTERVAL: Final = 60  # minutes
