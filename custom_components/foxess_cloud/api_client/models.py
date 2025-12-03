"""Data models for the FoxESS Cloud API client."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Inverter(BaseModel):
    """Representation of an inverter returned by the device list endpoint."""

    device_sn: str = Field(alias="deviceSN")
    module_sn: str = Field(alias="moduleSN")
    station_id: str = Field(alias="stationID")
    station_name: str = Field(alias="stationName")
    status: int | None = None
    has_battery: bool | None = Field(default=None, alias="hasBattery")
    device_type: str | None = Field(default=None, alias="deviceType")
    product_type: str | None = Field(default=None, alias="productType")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Inverter":
        """Create an inverter from API response data."""

        return cls.model_validate(data)


class InverterDetail(BaseModel):
    """Detailed inverter information."""

    device_sn: str = Field(alias="deviceSN")
    module_sn: str | None = Field(default=None, alias="moduleSN")
    station_id: str | None = Field(default=None, alias="stationID")
    station_name: str | None = Field(default=None, alias="stationName")
    status: int | None = None
    has_battery: bool | None = Field(default=None, alias="hasBattery")
    device_type: str | None = Field(default=None, alias="deviceType")
    product_type: str | None = Field(default=None, alias="productType")
    installer: str | None = None
    city: str | None = None
    country: str | None = None
    timezone: str | None = None
    capacity: float | None = None
    last_update_time: str | None = Field(default=None, alias="lastUpdateTime")
    connect_status: str | None = Field(default=None, alias="connectStatus")
    afci_version: str | None = Field(default=None, alias="afciVersion")
    manager_version: str | None = Field(default=None, alias="managerVersion")
    master_version: str | None = Field(default=None, alias="masterVersion")
    slave_version: str | None = Field(default=None, alias="slaveVersion")
    hardware_version: str | None = Field(default=None, alias="hardwareVersion")
    function: dict[str, Any] | None = None
    battery_list: list["BatteryInfo"] | None = Field(default=None, alias="batteryList")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "InverterDetail":
        """Create an inverter detail from API response data."""

        return cls.model_validate(data)


class BatteryInfo(BaseModel):
    """Battery info attached to a device."""

    battery_sn: str = Field(alias="batterySN")
    type: str | None = None
    version: str | None = None
    model: str | None = None
    capacity: float | int | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class BatterySoc(BaseModel):
    """Battery SOC settings for a device."""

    min_soc: int = Field(alias="minSoc")
    min_soc_on_grid: int = Field(alias="minSocOnGrid")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class Generation(BaseModel):
    """Daily/period generation values."""

    today: float
    month: float
    cumulative: float

    model_config = {"populate_by_name": True, "extra": "ignore"}


class SettingItem(BaseModel):
    """Device setting item metadata/value."""

    enum_list: list[str] | None = Field(default=None, alias="enumList")
    unit: str | None = None
    precision: float | int | None = None
    value: str | float | int | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class SettingWriteResult(BaseModel):
    """Result of setting update."""

    value: str | float | int | None = None
    unit: str | None = None
    precision: float | int | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class SchedulerGroup(BaseModel):
    """One scheduler time segment (v1 schema)."""

    enable: int
    start_hour: int = Field(alias="startHour")
    start_minute: int = Field(alias="startMinute")
    end_hour: int = Field(alias="endHour")
    end_minute: int = Field(alias="endMinute")
    work_mode: str = Field(alias="workMode")
    min_soc_on_grid: int = Field(alias="minSocOnGrid")
    fd_soc: int = Field(alias="fdSoc")
    fd_pwr: float = Field(alias="fdPwr")
    max_soc: int = Field(alias="maxSoc")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class SchedulerInfo(BaseModel):
    """Scheduler configuration for a device."""

    enable: int
    groups: list[SchedulerGroup]

    model_config = {"populate_by_name": True, "extra": "ignore"}


class SchedulerSetRequest(BaseModel):
    """Typed request body for scheduler set (v1)."""

    groups: list[SchedulerGroup]
    device_sn: str = Field(alias="deviceSN")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class ProductionPoint(BaseModel):
    """Single data point from production report."""

    variable: str
    unit: str | None = None
    values: list[float] = []
    time: list[str] | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class RealTimeVariable(BaseModel):
    """Real-time data point for a single variable."""

    variable: str
    unit: str | None = None
    name: str | None = None
    value: float | int | str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class RealTimeData(BaseModel):
    """Real-time data response for a device."""

    device_sn: str = Field(alias="deviceSN")
    datas: list[RealTimeVariable] = Field(alias="datas")
    time: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class RealTimeSnapshot(BaseModel):
    """Convenient mapping of real-time variables for a device."""

    device_sn: str
    time: str | None

    pvPower: RealTimeVariable | None = None
    pv1Volt: RealTimeVariable | None = None
    pv1Current: RealTimeVariable | None = None
    pv1Power: RealTimeVariable | None = None
    pv2Volt: RealTimeVariable | None = None
    pv2Current: RealTimeVariable | None = None
    pv2Power: RealTimeVariable | None = None
    pv3Volt: RealTimeVariable | None = None
    pv3Current: RealTimeVariable | None = None
    pv3Power: RealTimeVariable | None = None
    pv4Volt: RealTimeVariable | None = None
    pv4Current: RealTimeVariable | None = None
    pv4Power: RealTimeVariable | None = None
    epsPower: RealTimeVariable | None = None
    epsCurrentR: RealTimeVariable | None = None
    epsVoltR: RealTimeVariable | None = None
    epsPowerR: RealTimeVariable | None = None
    RCurrent: RealTimeVariable | None = None
    RVolt: RealTimeVariable | None = None
    RFreq: RealTimeVariable | None = None
    RPower: RealTimeVariable | None = None
    ambientTemperation: RealTimeVariable | None = None
    invTemperation: RealTimeVariable | None = None
    batTemperature: RealTimeVariable | None = None
    loadsPower: RealTimeVariable | None = None
    generationPower: RealTimeVariable | None = None
    feedinPower: RealTimeVariable | None = None
    gridConsumptionPower: RealTimeVariable | None = None
    invBatVolt: RealTimeVariable | None = None
    invBatCurrent: RealTimeVariable | None = None
    invBatPower: RealTimeVariable | None = None
    batChargePower: RealTimeVariable | None = None
    batDischargePower: RealTimeVariable | None = None
    batVolt: RealTimeVariable | None = None
    batCurrent: RealTimeVariable | None = None
    meterPower: RealTimeVariable | None = None
    meterPower2: RealTimeVariable | None = None
    SoC: RealTimeVariable | None = None
    generation: RealTimeVariable | None = None
    ResidualEnergy: RealTimeVariable | None = None
    runningState: RealTimeVariable | None = None
    batStatus: RealTimeVariable | None = None
    batStatusV2: RealTimeVariable | None = None
    currentFault: RealTimeVariable | None = None
    currentFaultCount: RealTimeVariable | None = None
    energyThroughput: RealTimeVariable | None = None
    SOH: RealTimeVariable | None = None
    gridConsumption: RealTimeVariable | None = None
    loads: RealTimeVariable | None = None
    feedin: RealTimeVariable | None = None
    chargeEnergyToTal: RealTimeVariable | None = None
    dischargeEnergyToTal: RealTimeVariable | None = None
    PVEnergyTotal: RealTimeVariable | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @classmethod
    def from_realtime(cls, data: RealTimeData) -> "RealTimeSnapshot":
        kwargs: dict[str, RealTimeVariable] = {}
        for item in data.datas:
            if item.variable in cls.model_fields:
                kwargs[item.variable] = item
        return cls(device_sn=data.device_sn, time=data.time, **kwargs)
