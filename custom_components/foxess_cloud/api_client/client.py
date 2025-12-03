"""Async FoxESS Cloud API client."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from hashlib import md5
import sys
from time import time
from typing import Any, Awaitable, Callable

from aiohttp import ClientResponseError, ClientSession

_SETTING_KEYS = {
    "exportlimit": "ExportLimit",
    "minsoc": "MinSoc",
    "minsocongrid": "MinSocOnGrid",
    "maxsoc": "MaxSoc",
    "gridcode": "GridCode",
    "workmode": "WorkMode",
    "activepowerlimit": "ActivePowerLimit",
    "exportlimitpower": "ExportLimitPower",
    "epsoutput": "EpsOutPut",
    "ecomode": "ECOMode",
}

from .errors import (
    FoxESSCloudApiError,
    FoxESSCloudAuthError,
    FoxESSCloudConnectionError,
)
from .models import (
    BatterySoc,
    Generation,
    Inverter,
    InverterDetail,
    ProductionPoint,
    SettingItem,
    SettingWriteResult,
    SchedulerSetRequest,
    SchedulerInfo,
    RealTimeSnapshot,
    RealTimeData,
    RealTimeVariable,
)

DEFAULT_BASE_URL = "https://www.foxesscloud.com"
DEFAULT_LANG = "en"
DEFAULT_TIMEZONE = "Europe/London"
DEFAULT_USER_AGENT = "HomeAssistant-FoxESSCloud/0.1"

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class FoxESSCloudClient:
    """Minimal async client for FoxESS Cloud OpenAPI."""

    api_key: str
    session: ClientSession
    on_api_call: Callable[[], Awaitable[None]] | None = None
    base_url: str = DEFAULT_BASE_URL
    lang: str = DEFAULT_LANG
    timezone: str = DEFAULT_TIMEZONE
    user_agent: str = DEFAULT_USER_AGENT
    min_interval: float = 2.0
    debug: bool = False
    _last_call: float = 0.0

    async def async_list_inverters(
        self, page: int = 1, page_size: int = 10
    ) -> list[Inverter]:
        """List inverters owned by the account (POST /op/v0/device/list)."""

        payload = {"currentPage": page, "pageSize": page_size}
        data = await self._async_post_json("/op/v0/device/list", payload)

        result = data.get("result", {})
        devices = result.get("data", [])
        return [Inverter.from_api(device) for device in devices]

    async def async_get_setting(self, sn: str, key: str) -> SettingItem:
        """Get a single device setting item (POST /op/v0/device/setting/get)."""

        canonical_key = self._canonical_setting_key(key)
        payload = {"sn": sn, "key": canonical_key}
        data = await self._async_post_json("/op/v0/device/setting/get", payload)
        result = data.get("result", {})
        return SettingItem.model_validate(result)

    async def async_set_setting(self, sn: str, key: str, value: str | float | int) -> SettingWriteResult:
        """Set a single device setting value (POST /op/v0/device/setting/set)."""

        canonical_key = self._canonical_setting_key(key)
        payload = {"sn": sn, "key": canonical_key, "value": value}
        data = await self._async_post_json("/op/v0/device/setting/set", payload)
        result = data.get("result")
        # Some responses return null result on success; accept that.
        if result is None:
            return SettingWriteResult()
        return SettingWriteResult.model_validate(result)

    async def async_get_device_detail(self, sn: str) -> InverterDetail:
        """Get detailed device info (GET /op/v1/device/detail)."""

        params = {"sn": sn}
        data = await self._async_get_json("/op/v1/device/detail", params)
        result = data.get("result", {})
        return InverterDetail.from_api(result)

    async def async_get_battery_soc(self, sn: str) -> BatterySoc:
        """Get battery min SOC settings (GET /op/v0/device/battery/soc/get)."""

        params = {"sn": sn}
        data = await self._async_get_json("/op/v0/device/battery/soc/get", params)
        result = data.get("result", {})
        return BatterySoc.model_validate(result)

    async def async_get_generation(self, sn: str) -> Generation:
        """Get today/month/cumulative generation (GET /op/v0/device/generation)."""

        params = {"sn": sn}
        data = await self._async_get_json("/op/v0/device/generation", params)
        result = data.get("result", {})
        return Generation.model_validate(result)

    async def async_get_production_report(
        self,
        sn: str,
        dimension: str,
        year: int,
        month: int | None = None,
        day: int | None = None,
        variables: list[str] | None = None,
    ) -> list[ProductionPoint]:
        """Get production report (year/month/day) via POST /op/v0/device/report/query."""

        if dimension not in {"year", "month", "day"}:
            raise FoxESSCloudApiError("dimension must be one of: year, month, day")

        payload: dict[str, Any] = {
            "sn": sn,
            "dimension": dimension,
            "year": year,
        }
        if month is not None:
            payload["month"] = month
        if day is not None:
            payload["day"] = day
        if variables:
            payload["variables"] = variables
        else:
            payload["variables"] = [
                "generation",
                "feedin",
                "gridConsumption",
                "chargeEnergyToTal",
                "dischargeEnergyToTal",
                "PVEnergyTotal",
            ]

        data = await self._async_post_json("/op/v0/device/report/query", payload)
        result = data.get("result", [])
        return [ProductionPoint.model_validate(item) for item in result]

    async def async_get_real_time_data(
        self,
        sns: list[str],
        variables: list[str] | None = None,
        api_version: str = "v1",
    ) -> list[RealTimeData]:
        """Get real-time data (POST /op/{v0|v1}/device/real/query)."""

        if not sns:
            raise FoxESSCloudApiError("sns must contain at least one serial number")

        if api_version not in {"v0", "v1"}:
            raise FoxESSCloudApiError("api_version must be 'v0' or 'v1'")

        if api_version == "v0":
            if len(sns) != 1:
                raise FoxESSCloudApiError("v0 real-time query accepts exactly one sn")
            payload: dict[str, Any] = {"sn": sns[0]}
        else:
            payload = {"sns": sns}

        if variables:
            payload["variables"] = variables

        path = f"/op/{api_version}/device/real/query"
        data = await self._async_post_json(path, payload)
        result = data.get("result", [])
        return [RealTimeData.model_validate(item) for item in result]

    async def async_get_real_time_snapshot(
        self, sn: str, variables: list[str] | None = None, api_version: str = "v1"
    ) -> RealTimeSnapshot:
        """Get real-time data for one device as a typed snapshot (wraps real/query)."""

        data = await self.async_get_real_time_data(
            sns=[sn], variables=variables, api_version=api_version
        )
        if not data:
            return RealTimeSnapshot(device_sn=sn, time=None, variables={})
        return RealTimeSnapshot.from_realtime(data[0])

    async def async_get_scheduler(self, sn: str) -> SchedulerInfo:
        """Get scheduler time-segment info (POST /op/v1/device/scheduler/get)."""

        payload = {"deviceSN": sn}
        data = await self._async_post_json("/op/v1/device/scheduler/get", payload)
        result = data.get("result", {})
        return SchedulerInfo.model_validate(result)

    async def async_set_scheduler(self, request: SchedulerSetRequest) -> None:
        """Set scheduler groups (POST /op/v1/device/scheduler/enable)."""

        payload = request.model_dump(by_alias=True, exclude_none=True)
        if self.debug:
            print(f"[foxess_cloud] SET SCHEDULER payload={payload}", file=sys.stderr)

        await self._async_post_json(
            "/op/v1/device/scheduler/enable",
            payload,
        )


    async def _async_post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform an authenticated POST request and return the parsed JSON."""

        _LOGGER.debug("FoxESS POST %s (payload keys=%s)", path, list(payload.keys()))

        await self._throttle()
        await self._record_api_call()
        timestamp = self._timestamp_ms()
        signature = self._generate_signature(path, timestamp)

        headers = {
            "Content-Type": "application/json",
            "Token": self.api_key,
            "Signature": signature,
            "Timestamp": timestamp,
            "Lang": self.lang,
            "Timezone": self.timezone,
            "User-Agent": self.user_agent,
            "Connection": "close",
        }

        url = f"{self.base_url}{path}"

        try:
            response = await self.session.post(
                url, json=payload, headers=headers, timeout=15, ssl=False
            )
            response.raise_for_status()
            data = await response.json()
            if self.debug:
                print(
                    f"[foxess_cloud] POST {url} payload={payload} errno={data.get('errno')} message={data.get('msg') or data.get('message')}",
                    file=sys.stderr,
                )
        except ClientResponseError as err:
            if err.status == 401:
                raise FoxESSCloudAuthError("Authentication failed") from err
            raise FoxESSCloudConnectionError("HTTP error during FoxESS Cloud request") from err
        except Exception as err:  # noqa: BLE001 - network call wrapper
            raise FoxESSCloudConnectionError("Failed to communicate with FoxESS Cloud") from err

        if not isinstance(data, dict):
            raise FoxESSCloudApiError("Unexpected response format from FoxESS Cloud")

        errno = data.get("errno")
        message = data.get("msg") or data.get("message") or data.get("error")
        if errno is None:
            raise FoxESSCloudApiError("Missing errno in FoxESS Cloud response")

        if errno != 0:
            # The API doesn't document error codes here; treat any non-zero as auth failure first.
            if errno in (401, 403):
                raise FoxESSCloudAuthError(
                    f"FoxESS Cloud authentication failed (errno {errno}: {message or 'no message'})"
                )
            raise FoxESSCloudApiError(
                f"FoxESS Cloud returned error code {errno}: {message or 'no message'}; result={data.get('result')}"
            )

        return data

    async def _async_get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Perform an authenticated GET request and return parsed JSON."""

        _LOGGER.debug("FoxESS GET %s (params=%s)", path, list(params.keys()))

        await self._throttle()
        await self._record_api_call()
        timestamp = self._timestamp_ms()
        signature = self._generate_signature(path, timestamp)

        headers = {
            "Content-Type": "application/json",
            "Token": self.api_key,
            "Signature": signature,
            "Timestamp": timestamp,
            "Lang": self.lang,
            "Timezone": self.timezone,
            "User-Agent": self.user_agent,
            "Connection": "close",
        }

        url = f"{self.base_url}{path}"

        try:
            response = await self.session.get(
                url, params=params, headers=headers, timeout=15, ssl=False
            )
            response.raise_for_status()
            data = await response.json()
            if self.debug:
                print(
                    f"[foxess_cloud] GET {response.url} errno={data.get('errno')} message={data.get('msg') or data.get('message')}",
                    file=sys.stderr,
                )
        except ClientResponseError as err:
            if err.status == 401:
                raise FoxESSCloudAuthError("Authentication failed") from err
            raise FoxESSCloudConnectionError("HTTP error during FoxESS Cloud request") from err
        except Exception as err:  # noqa: BLE001 - network call wrapper
            raise FoxESSCloudConnectionError("Failed to communicate with FoxESS Cloud") from err

        if not isinstance(data, dict):
            raise FoxESSCloudApiError("Unexpected response format from FoxESS Cloud")

        errno = data.get("errno")
        message = data.get("msg") or data.get("message") or data.get("error")
        if errno is None:
            raise FoxESSCloudApiError("Missing errno in FoxESS Cloud response")

        if errno != 0:
            if errno in (401, 403):
                raise FoxESSCloudAuthError(
                    f"FoxESS Cloud authentication failed (errno {errno}: {message or 'no message'})"
                )
            raise FoxESSCloudApiError(
                f"FoxESS Cloud returned error code {errno}: {message or 'no message'}; result={data.get('result')}"
            )

        return data

    async def _throttle(self) -> None:
        """Enforce minimum interval between calls."""

        now = time()
        delta = now - self._last_call
        if delta < self.min_interval:
            await asyncio.sleep(self.min_interval - delta)
        self._last_call = time()

    def _generate_signature(self, path: str, timestamp: str) -> str:
        """Generate request signature.

        Rule: md5 of f"{path}\r\n{token}\r\n{timestamp}".
        """

        # FoxESS expects literal backslash-r and backslash-n separators, not CRLF bytes.
        text = f"{path}\\r\\n{self.api_key}\\r\\n{timestamp}"
        digest = md5(text.encode(), usedforsecurity=False)
        return digest.hexdigest()

    def _canonical_setting_key(self, key: str) -> str:
        """Return canonical setting key as expected by the API."""

        normalized = key.replace("_", "").replace("-", "").lower()
        if canonical := _SETTING_KEYS.get(normalized):
            return canonical
        raise FoxESSCloudApiError(
            f"Unknown setting key '{key}'. Allowed keys: {', '.join(_SETTING_KEYS.values())}"
        )

    @staticmethod
    def _timestamp_ms() -> str:
        """Return current epoch timestamp in milliseconds as string."""

        return str(int(time() * 1000))

    async def _record_api_call(self) -> None:
        """Invoke the API call hook, if provided."""

        if self.on_api_call is not None:
            await self.on_api_call()
