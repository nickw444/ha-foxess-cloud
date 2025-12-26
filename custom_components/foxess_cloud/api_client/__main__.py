"""Minimal CLI for manual FoxESS Cloud API testing.

Usage examples (from repo root):
  PYTHONPATH=custom_components/foxess_cloud uv run python -m api_client.__main__ \\
      --api-key YOUR_KEY list-inverters

You can override the base URL for staging environments with --base-url.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from aiohttp import ClientSession
from .client import FoxESSCloudClient
from .errors import FoxESSCloudApiError, FoxESSCloudAuthError, FoxESSCloudConnectionError


async def _list_inverters(client: FoxESSCloudClient, args: argparse.Namespace) -> int:
    inverters = await client.async_list_inverters(
        page=args.page, page_size=args.page_size
    )
    print(json.dumps([inv.model_dump() for inv in inverters], indent=2))
    return 0


async def _run_command(args: argparse.Namespace) -> int:
    async with ClientSession() as session:
        client = FoxESSCloudClient(
            api_key=args.api_key,
            session=session,
            base_url=args.base_url,
            debug=args.debug,
        )

        try:
            if args.command == "list-inverters":
                return await _list_inverters(client, args)
            if args.command == "get-setting":
                setting = await client.async_get_setting(args.sn, args.key)
                print(json.dumps(setting.model_dump(), indent=2))
                return 0
            if args.command == "set-setting":
                # Attempt to coerce numeric strings to number when possible
                raw_value: str = args.value
                value: str | int | float
                try:
                    if "." in raw_value:
                        value = float(raw_value)
                    else:
                        value = int(raw_value)
                except ValueError:
                    value = raw_value
                result = await client.async_set_setting(args.sn, args.key, value)
                print(json.dumps(result.model_dump(), indent=2))
                return 0
            if args.command == "device-detail":
                detail = await client.async_get_device_detail(args.sn)
                print(json.dumps(detail.model_dump(), indent=2))
                return 0
            if args.command == "battery-soc":
                soc = await client.async_get_battery_soc(args.sn)
                print(json.dumps(soc.model_dump(), indent=2))
                return 0
            if args.command == "generation":
                gen = await client.async_get_generation(args.sn)
                print(json.dumps(gen.model_dump(), indent=2))
                return 0
            if args.command == "production-report":
                points = await client.async_get_production_report(
                    args.sn,
                    args.dimension,
                    args.year,
                    month=args.month,
                    day=args.day,
                    variables=args.variables or None,
                )
                print(json.dumps([p.model_dump() for p in points], indent=2))
                return 0
            if args.command == "real-time":
                rt = await client.async_get_real_time_data(
                    sns=args.sns, variables=args.variables or None, api_version=args.api_version
                )
                print(json.dumps([item.model_dump() for item in rt], indent=2))
                return 0
            if args.command == "real-time-snapshot":
                snap = await client.async_get_real_time_snapshot(
                    sn=args.sn, variables=args.variables or None, api_version=args.api_version
                )
                print(json.dumps(snap.model_dump(), indent=2))
                return 0
            if args.command == "scheduler":
                sched = await client.async_get_scheduler(args.sn)
                print(json.dumps(sched.model_dump(), indent=2))
                return 0
            if args.command == "scheduler-set-one":
                from .models import SchedulerGroup, SchedulerSetRequest

                group = SchedulerGroup(
                    enable=args.group_enable,
                    startHour=args.start_hour,
                    startMinute=args.start_minute,
                    endHour=args.end_hour,
                    endMinute=args.end_minute,
                    workMode=args.work_mode,
                    minSocOnGrid=args.min_soc_on_grid,
                    fdSoc=args.fd_soc,
                    fdPwr=args.fd_pwr,
                    maxSoc=args.max_soc,
                )
                request = SchedulerSetRequest(deviceSN=args.sn, groups=[group])
                await client.async_set_scheduler(request)
                print("OK")
                return 0
            if args.command == "scheduler-clear":
                from .models import SchedulerSetRequest

                request = SchedulerSetRequest(deviceSN=args.sn, groups=[])
                await client.async_set_scheduler(request)
                print("OK")
                return 0
        except FoxESSCloudAuthError as err:
            print(f"Auth failed: {err}", file=sys.stderr)
            return 2
        except FoxESSCloudConnectionError as err:
            print(f"Connection error: {err}", file=sys.stderr)
            return 3
        except FoxESSCloudApiError as err:
            print(f"API error: {err}", file=sys.stderr)
            return 4

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FoxESS Cloud API CLI")
    parser.add_argument("--api-key", required=True, help="FoxESS Cloud API key")
    parser.add_argument(
        "--base-url",
        default="https://www.foxesscloud.com",
        help="Override FoxESS Cloud base URL",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug info (request payload and errno/message) to stderr",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list-inverters", help="List inverters linked to the account"
    )
    list_parser.add_argument("--page", type=int, default=1, help="Page number")
    list_parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Items per page (minimum 10 per API docs)",
    )

    setting_parser = subparsers.add_parser(
        "get-setting", help="Get a device setting by key"
    )
    setting_parser.add_argument("--sn", required=True, help="Inverter serial number")
    setting_parser.add_argument("--key", required=True, help="Setting key to retrieve")

    setting_set_parser = subparsers.add_parser(
        "set-setting", help="Set a device setting value"
    )
    setting_set_parser.add_argument("--sn", required=True, help="Inverter serial number")
    setting_set_parser.add_argument("--key", required=True, help="Setting key to set")
    setting_set_parser.add_argument("--value", required=True, help="Value to set")

    detail_parser = subparsers.add_parser(
        "device-detail", help="Get detailed info for a device"
    )
    detail_parser.add_argument("--sn", required=True, help="Inverter serial number")

    soc_parser = subparsers.add_parser(
        "battery-soc", help="Get battery SOC settings for a device"
    )
    soc_parser.add_argument("--sn", required=True, help="Inverter serial number")

    gen_parser = subparsers.add_parser(
        "generation", help="Get generation totals (today/month/cumulative)"
    )
    gen_parser.add_argument("--sn", required=True, help="Inverter serial number")

    report_parser = subparsers.add_parser(
        "production-report", help="Get production report (year/month/day dimension)"
    )
    report_parser.add_argument("--sn", required=True, help="Inverter serial number")
    report_parser.add_argument("--dimension", required=True, choices=["year", "month", "day"])
    report_parser.add_argument("--year", type=int, required=True)
    report_parser.add_argument("--month", type=int)
    report_parser.add_argument("--day", type=int)
    report_parser.add_argument(
        "--variables",
        nargs="*",
        help="Optional list of variables. If omitted, all variables returned by API.",
    )

    realtime_parser = subparsers.add_parser(
        "real-time", help="Get real-time data for one or more devices"
    )
    realtime_parser.add_argument(
        "--sns", nargs="+", required=True, help="One or more inverter serial numbers"
    )
    realtime_parser.add_argument(
        "--variables",
        nargs="*",
        help="Optional variables list. If omitted, all variables are returned.",
    )
    realtime_parser.add_argument(
        "--api-version",
        choices=["v1", "v0"],
        default="v1",
        help="Real-time API version to use (default v1, fallback v0)",
    )

    realtime_snap_parser = subparsers.add_parser(
        "real-time-snapshot",
        help="Get real-time data for a single device mapped by variable name",
    )
    realtime_snap_parser.add_argument("--sn", required=True, help="Inverter serial number")
    realtime_snap_parser.add_argument(
        "--variables",
        nargs="*",
        help="Optional variables list. If omitted, all variables are returned.",
    )
    realtime_snap_parser.add_argument(
        "--api-version",
        choices=["v1", "v0"],
        default="v1",
        help="Real-time API version to use (default v1, fallback v0)",
    )

    scheduler_parser = subparsers.add_parser(
        "scheduler", help="Get scheduler (time segment) information"
    )
    scheduler_parser.add_argument("--sn", required=True, help="Inverter serial number")

    scheduler_set_parser = subparsers.add_parser(
        "scheduler-set-one",
        help="Set scheduler with a single group (v2 endpoint; other groups disabled)",
    )
    scheduler_set_parser.add_argument("--sn", required=True, help="Inverter serial number")
    scheduler_set_parser.add_argument("--enable", type=int, default=1, help="Scheduler master enable 0/1 (unused in v1 payload but kept for CLI symmetry)")
    scheduler_set_parser.add_argument("--group-enable", type=int, default=1, help="Group enable 0/1")
    scheduler_set_parser.add_argument("--start-hour", type=int, required=True)
    scheduler_set_parser.add_argument("--start-minute", type=int, required=True)
    scheduler_set_parser.add_argument("--end-hour", type=int, required=True)
    scheduler_set_parser.add_argument("--end-minute", type=int, required=True)
    scheduler_set_parser.add_argument("--work-mode", required=True, help="Work mode string (e.g., SelfUse, ForceCharge, ForceDischarge, PeakShaving)")
    scheduler_set_parser.add_argument("--min-soc-on-grid", type=int, required=True)
    scheduler_set_parser.add_argument("--fd-soc", type=int, required=True)
    scheduler_set_parser.add_argument("--fd-pwr", type=float, required=True)
    scheduler_set_parser.add_argument("--max-soc", type=int, required=True)

    scheduler_clear_parser = subparsers.add_parser(
        "scheduler-clear", help="Clear scheduler (sets empty groups array)"
    )
    scheduler_clear_parser.add_argument("--sn", required=True, help="Inverter serial number")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(_run_command(args))


if __name__ == "__main__":
    sys.exit(main())
