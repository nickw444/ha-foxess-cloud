"""Unit tests for scheduler_merge (no Home Assistant needed)."""

from __future__ import annotations

from datetime import time

import pytest

from api_client.models import SchedulerGroup
from scheduler_merge import (
    ForceChargeWindow,
    ScheduleMergeError,
    merge_force_charge,
    remove_force_charge,
    split_window,
)


def _group(mode: str, sh: int, sm: int, eh: int, em: int, enable: int = 1, fd_soc: int = 10) -> SchedulerGroup:
    return SchedulerGroup.model_validate(
        {
            "enable": enable,
            "startHour": sh,
            "startMinute": sm,
            "endHour": eh,
            "endMinute": em,
            "workMode": mode,
            "minSocOnGrid": 10,
            "fdSoc": fd_soc,
            "fdPwr": 0,
            "maxSoc": 100,
        }
    )


# Shape returned by scheduler/get on a real inverter: two active groups + 6 empty slots.
CURRENT = [
    _group("ForceCharge", 7, 0, 7, 59, fd_soc=35),
    _group("SelfUse", 0, 0, 23, 59),
    *[_group("Invalid", 0, 0, 0, 0, enable=0) for _ in range(6)],
]


def _window(**kw) -> ForceChargeWindow:
    base = dict(start=time(6, 30), end=time(7, 59), target_soc=35, power=1500, min_soc_on_grid=10)
    base.update(kw)
    return ForceChargeWindow(**base)


def test_merge_keeps_selfuse_and_replaces_existing_force_charge() -> None:
    merged = merge_force_charge(CURRENT, _window())
    modes = [(g.work_mode, g.start_hour, g.start_minute, g.end_hour, g.end_minute) for g in merged]
    assert modes == [("ForceCharge", 6, 30, 7, 59), ("SelfUse", 0, 0, 23, 59)]
    assert merged[0].fd_soc == 35 and merged[0].fd_pwr == 1500


def test_merge_drops_disabled_and_invalid_slots() -> None:
    merged = merge_force_charge(CURRENT, _window())
    assert all(g.enable == 1 and g.work_mode != "Invalid" for g in merged)


def test_merge_splits_midnight_window() -> None:
    merged = merge_force_charge([], _window(start=time(23, 0), end=time(2, 0)))
    assert [(g.start_hour, g.end_hour) for g in merged] == [(23, 23), (0, 2)]


def test_target_below_min_soc_rejected() -> None:
    with pytest.raises(ScheduleMergeError):
        merge_force_charge(CURRENT, _window(target_soc=10, min_soc_on_grid=20))


def test_too_many_groups_rejected() -> None:
    current = [_group("SelfUse", h, 0, h, 59) for h in range(8)]
    with pytest.raises(ScheduleMergeError):
        merge_force_charge(current, _window(), max_groups=8)


def test_bat_mode_supported_and_bad_mode_rejected() -> None:
    assert merge_force_charge([], _window(work_mode="ForceCharge(BAT)"))[0].work_mode == "ForceCharge(BAT)"
    with pytest.raises(ScheduleMergeError):
        merge_force_charge([], _window(work_mode="Feedin"))


def test_remove_force_charge_keeps_others() -> None:
    remaining = remove_force_charge(CURRENT)
    assert [g.work_mode for g in remaining] == ["SelfUse"]


def test_split_window_rejects_zero_length() -> None:
    with pytest.raises(ScheduleMergeError):
        split_window(time(7, 0), time(7, 0))


def test_payload_shape_matches_api() -> None:
    payload = merge_force_charge(CURRENT, _window())[0].model_dump(by_alias=True, exclude_none=True)
    assert set(payload) == {
        "enable", "startHour", "startMinute", "endHour", "endMinute",
        "workMode", "minSocOnGrid", "fdSoc", "fdPwr", "maxSoc",
    }


def test_remove_force_charge_falls_back_to_selfuse_when_nothing_remains() -> None:
    only_fc = [_group("ForceCharge", 6, 0, 7, 59, fd_soc=35)]
    remaining = remove_force_charge(only_fc)
    assert len(remaining) == 1
    g = remaining[0]
    assert (g.work_mode, g.start_hour, g.start_minute, g.end_hour, g.end_minute) == ("SelfUse", 0, 0, 23, 59)
    assert g.min_soc_on_grid == 10 and g.fd_soc == 10
