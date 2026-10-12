"""Pure helpers to merge force-charge windows into an existing schedule.

Kept free of Home Assistant imports so the logic can be unit tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

try:
    from .api_client.models import SchedulerGroup
except ImportError:  # imported as a top-level module (unit tests / CLI PYTHONPATH)
    from api_client.models import SchedulerGroup  # type: ignore[no-redef]

FORCE_CHARGE_MODES: frozenset[str] = frozenset({"ForceCharge", "ForceCharge(BAT)"})
# Work modes returned by scheduler/get for unused slots; never written back.
IGNORED_WORK_MODES: frozenset[str] = frozenset({"Invalid", ""})
DEFAULT_MAX_GROUPS = 8


class ScheduleMergeError(ValueError):
    """Raised when a merged schedule cannot be built."""


@dataclass(frozen=True, slots=True)
class ForceChargeWindow:
    """A force-charge request expressed in user-facing terms."""

    start: time
    end: time
    target_soc: int
    power: float
    min_soc_on_grid: int
    max_soc: int = 100
    work_mode: str = "ForceCharge"


def split_window(start: time, end: time) -> list[tuple[int, int, int, int]]:
    """Return (start_h, start_m, end_h, end_m) tuples, splitting windows that cross midnight."""

    if (start.hour, start.minute) == (end.hour, end.minute):
        raise ScheduleMergeError("start and end must differ")
    if (end.hour, end.minute) > (start.hour, start.minute):
        return [(start.hour, start.minute, end.hour, end.minute)]
    segments = [(start.hour, start.minute, 23, 59)]
    if (end.hour, end.minute) != (0, 0):
        segments.append((0, 0, end.hour, end.minute))
    return segments


def window_to_groups(window: ForceChargeWindow) -> list[SchedulerGroup]:
    """Build scheduler groups for a force-charge window."""

    if window.work_mode not in FORCE_CHARGE_MODES:
        raise ScheduleMergeError(f"work_mode must be one of {sorted(FORCE_CHARGE_MODES)}")
    if window.target_soc < window.min_soc_on_grid:
        # FoxESS docs: "value of fdsoc must be equal or greater than minSocOnGrid".
        raise ScheduleMergeError("target_soc must be >= min_soc_on_grid")
    return [
        SchedulerGroup(
            enable=1,
            start_hour=sh,
            start_minute=sm,
            end_hour=eh,
            end_minute=em,
            work_mode=window.work_mode,
            min_soc_on_grid=window.min_soc_on_grid,
            fd_soc=window.target_soc,
            fd_pwr=window.power,
            max_soc=window.max_soc,
        )
        for sh, sm, eh, em in split_window(window.start, window.end)
    ]


def kept_groups(current: list[SchedulerGroup]) -> list[SchedulerGroup]:
    """Enabled, real groups that are not force-charge windows (e.g. a SelfUse base)."""

    return [
        g.model_copy()
        for g in current
        if g.enable == 1
        and g.work_mode not in IGNORED_WORK_MODES
        and g.work_mode not in FORCE_CHARGE_MODES
    ]


def merge_force_charge(
    current: list[SchedulerGroup],
    window: ForceChargeWindow,
    max_groups: int = DEFAULT_MAX_GROUPS,
) -> list[SchedulerGroup]:
    """Replace existing force-charge groups with `window`, keeping every other enabled group."""

    merged = window_to_groups(window) + kept_groups(current)
    if len(merged) > max_groups:
        raise ScheduleMergeError(
            f"merged schedule needs {len(merged)} groups but the inverter supports {max_groups}"
        )
    return merged


def selfuse_all_day(min_soc_on_grid: int = 10) -> SchedulerGroup:
    """A single 00:00-23:59 SelfUse group."""

    return SchedulerGroup(
        enable=1,
        start_hour=0,
        start_minute=0,
        end_hour=23,
        end_minute=59,
        work_mode="SelfUse",
        min_soc_on_grid=min_soc_on_grid,
        fd_soc=min_soc_on_grid,
        fd_pwr=0,
        max_soc=100,
    )


def remove_force_charge(current: list[SchedulerGroup]) -> list[SchedulerGroup]:
    """Drop force-charge groups (and empty slots), keeping every other enabled group.

    If nothing would remain, return a single 00:00-23:59 SelfUse group instead of an
    empty list: an empty ``groups`` payload is accepted by the API but does not clear
    the inverter schedule (see issue #6), which would leave the ForceCharge window active.
    """

    remaining = kept_groups(current)
    if remaining:
        return remaining
    min_soc = next((g.min_soc_on_grid for g in current if g.enable == 1), 10)
    return [selfuse_all_day(min_soc)]
