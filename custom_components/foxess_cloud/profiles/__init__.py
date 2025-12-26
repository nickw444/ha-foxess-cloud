"""Series profiles for FoxESS devices."""

from __future__ import annotations

from ..api_client.models import InverterDetail
from .base import DeviceSeriesProfile
from .h3 import H3DeviceSeriesProfile
from .kh import KhDeviceSeriesProfile

__all__ = ["DeviceSeriesProfile", "select_device_series_profile"]

_PRODUCT_TYPE_EXACT_MATCH: dict[str, type[DeviceSeriesProfile]] = {
    # KH series (known product types)
    "KH": KhDeviceSeriesProfile,

    # H3 series (known product types)
    "H3-G2": H3DeviceSeriesProfile,
}


def select_device_series_profile(detail: InverterDetail | None) -> DeviceSeriesProfile:
    """Select the best profile for a device based on inverter detail."""

    product_type = (detail.product_type or "").strip().upper() if detail is not None else ""

    # Prefer strict matching on product_type.
    if profile := _PRODUCT_TYPE_EXACT_MATCH.get(product_type):
        return profile()

    # Best-effort fallback for product types not explicitly mapped.
    if product_type.startswith("H3"):
        return H3DeviceSeriesProfile()

    return KhDeviceSeriesProfile()
