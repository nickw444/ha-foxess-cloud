"""Sensor platform for FoxESS Cloud."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import FoxESSCloudDeviceDetailCoordinator, FoxESSCloudRealTimeCoordinator
from .api_call_tracker import ApiCallTracker

_LOGGER = logging.getLogger(__name__)


def _map_running_state(value: Any) -> str | None:
    """Return human readable running state without raw code."""

    if value is None:
        return None

    code = str(value)
    mapping = {
        "160": "Self test",
        "161": "Waiting",
        "162": "Checking",
        "163": "On grid",
        "164": "Off grid",
        "165": "Fault",
        "166": "Permanent fault",
        "167": "Standby",
        "168": "Upgrading",
        "169": "Factory test",
        "170": "Illegal",
    }

    if code in mapping:
        return mapping[code]

    _LOGGER.debug("Unknown running state code: %s", code)
    return "unknown"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FoxESS Cloud sensors from a config entry."""

    runtime_data = entry.runtime_data
    coordinator: FoxESSCloudRealTimeCoordinator = runtime_data.realtime_coordinator
    detail_coordinator: FoxESSCloudDeviceDetailCoordinator = runtime_data.device_detail_coordinator
    api_call_tracker: ApiCallTracker = runtime_data.api_call_tracker

    device_sn = entry.data[CONF_DEVICE_SN]
    device_info = runtime_data.device_info

    async_add_entities(
        [
            FoxESSLastUpdateSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSDeviceDetailSensor(
                coordinator=detail_coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSApiCallCountSensor(
                tracker=api_call_tracker,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSBatteryCapacitySensor(
                coordinator=detail_coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSInverterCapacitySensor(
                coordinator=detail_coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pvPower",
                translation_key="pv_power",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv1Volt",
                translation_key="pv1_voltage",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv1Current",
                translation_key="pv1_current",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv1Power",
                translation_key="pv1_power",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv2Volt",
                translation_key="pv2_voltage",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv2Current",
                translation_key="pv2_current",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv2Power",
                translation_key="pv2_power",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv3Volt",
                translation_key="pv3_voltage",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv3Current",
                translation_key="pv3_current",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv3Power",
                translation_key="pv3_power",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv4Volt",
                translation_key="pv4_voltage",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv4Current",
                translation_key="pv4_current",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="pv4Power",
                translation_key="pv4_power",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="epsPower",
                translation_key="eps_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="epsCurrentR",
                translation_key="eps_current",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="epsVoltR",
                translation_key="eps_voltage",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="epsPowerR",
                translation_key="eps_power_r",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="RCurrent",
                translation_key="r_current",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="RVolt",
                translation_key="grid_voltage",                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="RFreq",
                translation_key="grid_frequency",                device_class=SensorDeviceClass.FREQUENCY,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfFrequency.HERTZ,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="RPower",
                translation_key="r_power",
                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="ambientTemperation",
                translation_key="ambient_temperature",                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="invTemperation",
                translation_key="inverter_temperature",                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batTemperature",
                translation_key="battery_temperature",                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="loadsPower",
                translation_key="loads_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="generationPower",
                translation_key="generation_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="feedinPower",
                translation_key="feedin_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="gridConsumptionPower",
                translation_key="grid_consumption_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="invBatVolt",
                translation_key="inverter_battery_voltage",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="invBatCurrent",
                translation_key="inverter_battery_current",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="invBatPower",
                translation_key="inverter_battery_power",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batChargePower",
                translation_key="battery_charge_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batDischargePower",
                translation_key="battery_discharge_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batVolt",
                translation_key="battery_voltage",                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batCurrent",
                translation_key="battery_current",                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="meterPower",
                translation_key="meter_power",                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="meterPower2",
                translation_key="meter_power_2",                entity_registry_enabled_default=False,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="SoC",
                translation_key="battery_soc",                device_class=SensorDeviceClass.BATTERY,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement="%",
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="generation",
                translation_key="generation",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="ResidualEnergy",
                translation_key="residual_energy",                state_class=SensorStateClass.TOTAL,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRunningStateSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batStatus",
                translation_key="battery_status",            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="batStatusV2",
                translation_key="battery_status_v2",            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="currentFaultCount",
                translation_key="current_fault_count",                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement="faults",
                value_converter=lambda v: int(float(v)),
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="energyThroughput",
                translation_key="energy_throughput",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="SOH",
                translation_key="battery_soh",                device_class=SensorDeviceClass.BATTERY,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement="%",
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="gridConsumption",
                translation_key="grid_consumption",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="loads",
                translation_key="loads",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="feedin",
                translation_key="feedin",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="chargeEnergyToTal",
                translation_key="charge_energy_total",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="dischargeEnergyToTal",
                translation_key="discharge_energy_total",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
            FoxESSRealTimeSensor(
                coordinator=coordinator,
                device_sn=device_sn,
                device_info=device_info,
                variable_key="PVEnergyTotal",
                translation_key="pv_energy_total",                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_converter=float,
            ),
        ]
    )


class FoxESSRealTimeSensor(CoordinatorEntity[FoxESSCloudRealTimeCoordinator], SensorEntity):
    """FoxESS real-time sensor with runtime configuration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FoxESSCloudRealTimeCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
        *,
        variable_key: str,
        translation_key: str,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        native_unit_of_measurement: str | None = None,
        value_converter: Callable[[Any], Any] | None = None,
        entity_category: EntityCategory | None = None,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        super().__init__(coordinator)

        self._variable_key = variable_key
        self._value_converter = value_converter

        self._attr_unique_id = f"{device_sn}_{variable_key}"
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_info = device_info
        self._attr_entity_category = entity_category
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default

    @property
    def native_value(self) -> Any:
        """Return the current value for this sensor."""

        snapshot = self.coordinator.data
        if snapshot is None:
            return None

        variable = getattr(snapshot, self._variable_key, None)
        if variable is None:
            return None

        value = getattr(variable, "value", None)
        if self._value_converter is not None and value is not None:
            try:
                return self._value_converter(value)
            except (TypeError, ValueError):
                return None

        return value


class FoxESSRunningStateSensor(FoxESSRealTimeSensor):
    """Sensor exposing mapped running state with raw code as attribute."""

    def __init__(
        self,
        coordinator: FoxESSCloudRealTimeCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            device_sn=device_sn,
            device_info=device_info,
            variable_key="runningState",
            translation_key="running_state",
            value_converter=_map_running_state,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        self._raw_value: str | None = None

    @property
    def native_value(self) -> str | None:
        snapshot = self.coordinator.data
        if snapshot is None:
            return None

        variable = getattr(snapshot, "runningState", None)
        if variable is None:
            return None

        raw = getattr(variable, "value", None)
        self._raw_value = str(raw) if raw is not None else None

        if raw is None:
            return None

        return _map_running_state(raw)

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {"raw": self._raw_value}


class FoxESSLastUpdateSensor(CoordinatorEntity[FoxESSCloudRealTimeCoordinator], SensorEntity):
    """Sensor exposing the last update time from the realtime snapshot."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_update_time"

    def __init__(
        self,
        coordinator: FoxESSCloudRealTimeCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_last_update_time"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> datetime | None:
        snapshot = self.coordinator.data
        if snapshot is None or snapshot.time is None:
            return None

        time_str = snapshot.time.strip()

        # Expected format: "YYYY-MM-DD HH:MM:SS TZ+offset" (e.g., 2025-12-03 15:54:06 AEDT+1100)
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %Z%z")
        except ValueError:
            _LOGGER.debug("Invalid snapshot time format: %s", snapshot.time)
            return None


class FoxESSDeviceDetailSensor(CoordinatorEntity[FoxESSCloudDeviceDetailCoordinator], SensorEntity):
    """Diagnostic sensor exposing raw device detail data."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "device_detail"

    def __init__(
        self,
        coordinator: FoxESSCloudDeviceDetailCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_device_detail"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        detail = self.coordinator.data
        if detail is None:
            return None

        return detail.connect_status or (str(detail.status) if detail.status is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        detail = self.coordinator.data
        if detail is None:
            return None

        return {
            "detail": detail.model_dump(by_alias=True, exclude_none=True),
        }


class FoxESSBatteryCapacitySensor(CoordinatorEntity[FoxESSCloudDeviceDetailCoordinator], SensorEntity):
    """Total battery capacity across attached batteries."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "battery_capacity_total"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = None

    def __init__(
        self,
        coordinator: FoxESSCloudDeviceDetailCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_battery_capacity_total"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        detail = self.coordinator.data
        if detail is None or detail.battery_list is None:
            return None

        total_wh = sum(
            battery.capacity for battery in detail.battery_list if battery.capacity is not None
        )
        if total_wh is None:
            return None
        try:
            return float(total_wh) / 1000
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        detail = self.coordinator.data
        if detail is None or detail.battery_list is None:
            return None

        batteries = [
            battery.model_dump(by_alias=True, exclude_none=True)
            for battery in detail.battery_list
        ]
        counted = [b for b in detail.battery_list if b.capacity not in (None, 0)]
        return {
            "battery_count": len(counted),
            "batteries": batteries,
        }


class FoxESSInverterCapacitySensor(CoordinatorEntity[FoxESSCloudDeviceDetailCoordinator], SensorEntity):
    """Inverter nameplate capacity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "inverter_capacity"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: FoxESSCloudDeviceDetailCoordinator,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_sn}_inverter_capacity"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        detail = self.coordinator.data
        if detail is None or detail.capacity is None:
            return None
        try:
            return float(detail.capacity)
        except (TypeError, ValueError):
            return None


class FoxESSApiCallCountSensor(SensorEntity):
    """Diagnostic sensor exposing rolling 24h API call count."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "api_calls_24h"
    _attr_native_unit_of_measurement = "calls"
    _attr_scan_interval = timedelta(seconds=15)

    def __init__(
        self,
        tracker: ApiCallTracker,
        device_sn: str,
        device_info: DeviceInfo,
    ) -> None:
        self._attr_unique_id = f"{device_sn}_api_calls_24h"
        self._attr_device_info = device_info
        self._tracker = tracker

    @property
    def native_value(self) -> int | None:
        return self._attr_native_value

    async def async_update(self) -> None:
        self._attr_native_value = await self._tracker.count_last_24h()
