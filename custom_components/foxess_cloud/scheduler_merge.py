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


def _start(g: SchedulerGroup) -> int:
    return g.start_hour * 60 + g.start_minute


def _end(g: SchedulerGroup) -> int:
    return g.end_hour * 60 + g.end_minute


def _with_span(g: SchedulerGroup, start: int, end: int) -> SchedulerGroup:
    sh, sm = divmod(start, 60)
    eh, em = divmod(end, 60)
    return g.model_copy(update={"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em})


def find_overlaps(groups: list[SchedulerGroup]) -> list[tuple[int, int]]:
    """Index pairs of enabled groups whose time spans overlap (start and end minutes inclusive)."""

    active = [(i, _start(g), _end(g)) for i, g in enumerate(groups) if g.enable == 1]
    return [
        (i, j)
        for x, (i, a1, b1) in enumerate(active)
        for (j, a2, b2) in active[x + 1 :]
        if a1 <= b2 and a2 <= b1
    ]


def subtract_windows(groups: list[SchedulerGroup], windows: list[tuple[int, int]]) -> list[SchedulerGroup]:
    """Cut the minute ranges in `windows` out of every group, splitting groups as needed."""

    result = list(groups)
    for w_start, w_end in windows:
        trimmed: list[SchedulerGroup] = []
        for g in result:
            a, b = _start(g), _end(g)
            if b < w_start or a > w_end:
                trimmed.append(g)
                continue
            if a < w_start:
                trimmed.append(_with_span(g, a, w_start - 1))
            if b > w_end:
                trimmed.append(_with_span(g, w_end + 1, b))
        result = trimmed
    return result


def merge_force_charge(
    current: list[SchedulerGroup],
    window: ForceChargeWindow,
    max_groups: int = DEFAULT_MAX_GROUPS,
) -> list[SchedulerGroup]:
    """Replace existing force-charge groups with `window`, keeping every other enabled group.

    The kept groups are trimmed around the window: the FoxESS app refuses overlapping
    periods, and a ForceCharge window written on top of a 00:00-23:59 SelfUse group did not
    run on a real inverter. The result is sorted by start time.
    """

    charge = window_to_groups(window)
    kept = subtract_windows(_rejoin(kept_groups(current), current), [(_start(g), _end(g)) for g in charge])
    merged = sorted(charge + kept, key=_start)
    if find_overlaps(merged):
        raise ScheduleMergeError("merged schedule still has overlapping groups")
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


def _same_settings(a: SchedulerGroup, b: SchedulerGroup) -> bool:
    keys = ("enable", "work_mode", "min_soc_on_grid", "fd_soc", "fd_pwr", "max_soc")
    return all(getattr(a, k) == getattr(b, k) for k in keys)


def _rejoin(kept: list[SchedulerGroup], current: list[SchedulerGroup]) -> list[SchedulerGroup]:
    """Re-join groups that were split around a force-charge window.

    Two kept groups with identical settings are merged when the gap between them is fully
    covered by force-charge groups of `current`, so removing (or moving) the window restores
    e.g. a single 00:00-23:59 SelfUse group.
    """

    fc_minutes: set[int] = set()
    for g in current:
        if g.enable == 1 and g.work_mode in FORCE_CHARGE_MODES:
            fc_minutes.update(range(_start(g), _end(g) + 1))
    out: list[SchedulerGroup] = []
    for g in sorted(kept, key=_start):
        if out:
            prev = out[-1]
            gap = range(_end(prev) + 1, _start(g))
            if _same_settings(prev, g) and all(m in fc_minutes for m in gap):
                out[-1] = _with_span(prev, _start(prev), max(_end(prev), _end(g)))
                continue
        out.append(g)
    return out


def remove_force_charge(current: list[SchedulerGroup]) -> list[SchedulerGroup]:
    """Drop force-charge groups (and empty slots), keeping every other enabled group.

    Groups that were split around a force-charge window are joined again (see ``_rejoin``).

    If nothing would remain, return a single 00:00-23:59 SelfUse group instead of an
    empty list: an empty ``groups`` payload is accepted by the API but does not clear
    the inverter schedule (see issue #6), which would leave the ForceCharge window active.
    """

    remaining = _rejoin(kept_groups(current), current)
    if remaining:
        return remaining
    min_soc = next((g.min_soc_on_grid for g in current if g.enable == 1), 10)
    return [selfuse_all_day(min_soc)]
