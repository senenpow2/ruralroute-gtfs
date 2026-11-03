"""Command-line interface for repeatable journey-home feasibility checks."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

from .feed import Feed, GTFSDataError, seconds
from .planner import ReturnAssessment, assess_return
from .report import render_html


def _time(value: str) -> int:
    try:
        return seconds(value)
    except GTFSDataError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must be YYYY-MM-DD") from exc


def _windows(args: argparse.Namespace) -> tuple[int, int, int, int]:
    """Interpret a later, smaller clock time as the next day (up to 48 hours)."""
    raw = [args.outbound_after, args.arrive_by, args.return_after, args.home_by]
    values = [raw[0]]
    for value in raw[1:]:
        while value < values[-1]:
            value += 86400
        values.append(value)
    if values[-1] > 172800:
        raise ValueError("Travel windows may not exceed 48 hours")
    return tuple(values)


def _format_time(offset: int) -> str:
    day, secs = divmod(offset, 86400)
    hr, remain = divmod(secs, 3600)
    minute = remain // 60
    return f"{hr:02d}:{minute:02d}" + (f" (+{day}d)" if day else "")


def _human(feed: Feed, assessment: ReturnAssessment) -> str:
    origin = feed.stops[assessment.origin].name
    target = feed.stops[assessment.destination].name
    lines = [f"{origin} → {target} | {assessment.service_date}"]
    lines.append(f"Status: {assessment.status.replace('_', ' ').upper()}")
    for label, journey in (("Outbound", assessment.outbound), ("Return", assessment.inbound)):
        if not journey:
            lines.append(f"{label}: no matching scheduled journey")
            continue
        lines.append(f"{label}: {_format_time(journey.departure)} → {_format_time(journey.arrival)} ({len(journey.legs)} vehicle(s))")
        for leg in journey.legs:
            lines.append(
                f"  {feed.stops[leg.from_stop].name} {_format_time(leg.departure)} → "
                f"{feed.stops[leg.to_stop].name} {_format_time(leg.arrival)} "
                f"[{leg.route_id or leg.trip_id}]"
            )
    lines.append("Schedule-only estimate: not a guarantee of service, access or safe connections.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ruralroute",
        description="Offline GTFS timetable return-feasibility checker (no API keys).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    stops = sub.add_parser("stops", help="List stop IDs and names")
    stops.add_argument("--feed", required=True, type=Path)
    stops.add_argument("--filter", default="", help="Case-insensitive name/ID search")
    for command in ("check", "audit"):
        p = sub.add_parser(command, help="Check one destination" if command == "check" else "Check all destinations")
        p.add_argument("--feed", required=True, type=Path, help="GTFS ZIP or folder")
        p.add_argument("--date", required=True, type=_date, help="Service calendar date YYYY-MM-DD")
        p.add_argument("--from", required=True, dest="origin", help="Origin stop_id")
        if command == "check":
            p.add_argument("--to", required=True, dest="destination", help="Destination stop_id")
        else:
            p.add_argument("--limit", type=int, default=0, help="Limit destinations (0 = all)")
        p.add_argument("--outbound-after", type=_time, default=seconds("08:00"))
        p.add_argument("--arrive-by", type=_time, default=seconds("12:00"))
        p.add_argument("--return-after", type=_time, default=seconds("17:00"))
        p.add_argument("--home-by", type=_time, default=seconds("23:00"))
        p.add_argument("--min-transfer", type=int, default=5, help="Minutes needed to change vehicles")
        p.add_argument("--max-transfers", type=int, default=3)
        p.add_argument("--format", choices=("text", "json", "csv", "html"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        feed = Feed(args.feed)
        if args.command == "stops":
            for stop in sorted(feed.stops.values(), key=lambda s: (s.name.lower(), s.id)):
                if args.filter.lower() in (stop.id + " " + stop.name).lower():
                    print(f"{stop.id}\t{stop.name}")
            return 0
        if args.origin not in feed.stops:
            raise ValueError(f"Unknown origin stop_id {args.origin!r}; use 'ruralroute stops'")
        if args.min_transfer < 0 or args.max_transfers < 0:
            raise ValueError("Transfer settings cannot be negative")
        windows = _windows(args)
        destinations = ([args.destination] if args.command == "check" else
                        sorted(s for s in feed.stops if s != args.origin))
        if args.command == "audit":
            if args.limit < 0:
                raise ValueError("--limit must be >= 0")
            destinations = destinations[:args.limit] if args.limit else destinations
        stream = feed.connections(args.date, horizon=windows[3])
        results = [assess_return(
            feed, args.date, args.origin, dest, *windows,
            min_transfer=args.min_transfer * 60, max_transfers=args.max_transfers,
            connections=stream,
        ) for dest in destinations]
        if args.format == "html":
            print(render_html(feed, results, title="RuralRoute return-journey audit"))
        elif args.format == "json":
            print(json.dumps({
                "disclaimer": "GTFS scheduled service only; no realtime/fare/walking/accessibility assurances",
                "results": [result.to_dict() for result in results],
            }, indent=2))
        elif args.format == "csv":
            output = csv.writer(sys.stdout)
            output.writerow(("date", "origin_id", "destination_id", "destination_name", "status",
                             "outbound_arrival", "return_arrival", "outbound_vehicles", "return_vehicles"))
            for r in results:
                output.writerow((r.service_date, r.origin, r.destination, feed.stops[r.destination].name,
                                 r.status, _format_time(r.outbound.arrival) if r.outbound else "",
                                 _format_time(r.inbound.arrival) if r.inbound else "",
                                 len(r.outbound.legs) if r.outbound else "",
                                 len(r.inbound.legs) if r.inbound else ""))
        else:
            for result in results:
                print(_human(feed, result))
                if len(results) > 1:
                    print()
            if len(results) > 1:
                counts = {key: sum(r.status == key for r in results)
                          for key in ("round_trip_found", "no_outbound", "no_return")}
                print("Summary: " + ", ".join(f"{key}={count}" for key, count in counts.items()))
        return 0
    except (GTFSDataError, ValueError, OSError, KeyError) as exc:
        print(f"ruralroute: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
