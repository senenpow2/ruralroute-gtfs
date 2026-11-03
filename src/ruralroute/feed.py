"""Dependency-free reader for the explicitly documented subset of GTFS Schedule."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from io import TextIOWrapper
from pathlib import Path
from zipfile import BadZipFile, ZipFile


class GTFSDataError(ValueError):
    """A feed cannot be interpreted safely for the supported timetable subset."""


def seconds(value: str) -> int:
    """GTFS service-day HH:MM:SS, including hours beyond 23."""
    parts = value.strip().split(":")
    if len(parts) not in (2, 3) or not all(x.isascii() and x.isdigit() for x in parts):
        raise GTFSDataError(f"Invalid GTFS time: {value!r}")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    if not (0 <= hour <= 72 and 0 <= minute < 60 and 0 <= second < 60):
        raise GTFSDataError(f"GTFS time out of supported range: {value!r}")
    return hour * 3600 + minute * 60 + second


def service_date(value: str) -> date:
    try:
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8])) if len(value) == 8 else date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise GTFSDataError(f"Invalid service date: {value!r}") from exc


@dataclass(frozen=True)
class Stop:
    id: str
    name: str


@dataclass(frozen=True)
class StopCall:
    stop_id: str
    arrival: int
    departure: int
    sequence: int
    pickup: bool
    dropoff: bool


@dataclass(frozen=True)
class Trip:
    id: str
    service_id: str
    route_id: str
    calls: tuple[StopCall, ...]


@dataclass(frozen=True)
class Connection:
    instance_id: str
    trip_id: str
    route_id: str
    from_stop: str
    to_stop: str
    departure: int  # seconds offset from requested calendar date midnight
    arrival: int
    pickup: bool
    dropoff: bool


class Feed:
    """Load a GTFS ZIP or directory; make active schedule connections on demand.

    Scope deliberately excludes frequencies.txt, flex routes, timed transfers, station
    hierarchy, live disruptions and pedestrian routing. See docs/LIMITATIONS.md.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise GTFSDataError(f"Feed not found: {self.path}")
        self._zip = None
        try:
            if self.path.is_file():
                self._zip = ZipFile(self.path)
                self._names = set(self._zip.namelist())
            elif self.path.is_dir():
                self._names = {p.name for p in self.path.iterdir() if p.is_file()}
            else:
                raise GTFSDataError("Feed must be a GTFS ZIP file or directory")
            for required in ("stops.txt", "trips.txt", "stop_times.txt"):
                if required not in self._names:
                    raise GTFSDataError(f"Missing required feed file: {required}")
            if not ({"calendar.txt", "calendar_dates.txt"} & self._names):
                raise GTFSDataError("Expected calendar.txt and/or calendar_dates.txt")
            self.stops = self._load_stops()
            self.calendar = self._load_calendar()
            self.exceptions = self._load_exceptions()
            self.trips = self._load_trips()
        except (BadZipFile, UnicodeError, csv.Error) as exc:
            raise GTFSDataError(f"Invalid GTFS feed: {exc}") from exc
        finally:
            if self._zip:
                self._zip.close()
                self._zip = None

    def _rows(self, filename: str) -> list[dict[str, str]]:
        if filename not in self._names:
            return []
        if self._zip:
            with self._zip.open(filename) as binary:
                with TextIOWrapper(binary, encoding="utf-8-sig", newline="") as file:
                    return list(csv.DictReader(file))
        with (self.path / filename).open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _load_stops(self) -> dict[str, Stop]:
        stops = {}
        for row in self._rows("stops.txt"):
            stop_id = (row.get("stop_id") or "").strip()
            if not stop_id or stop_id in stops:
                raise GTFSDataError("Missing or duplicate stop_id in stops.txt")
            stops[stop_id] = Stop(stop_id, row.get("stop_name") or stop_id)
        if not stops:
            raise GTFSDataError("No stops in feed")
        return stops

    def _load_calendar(self) -> dict[str, tuple[date, date, tuple[bool, ...]]]:
        calendar = {}
        weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        for row in self._rows("calendar.txt"):
            service = row.get("service_id") or ""
            if not service or service in calendar:
                raise GTFSDataError("Missing or duplicate service_id in calendar.txt")
            calendar[service] = (
                service_date(row.get("start_date") or ""),
                service_date(row.get("end_date") or ""),
                tuple(row.get(day) == "1" for day in weekdays),
            )
        return calendar

    def _load_exceptions(self) -> dict[tuple[str, date], bool]:
        overrides = {}
        for row in self._rows("calendar_dates.txt"):
            service = row.get("service_id") or ""
            day = service_date(row.get("date") or "")
            change = row.get("exception_type")
            if not service or change not in ("1", "2") or (service, day) in overrides:
                raise GTFSDataError("Invalid or duplicate calendar_dates exception")
            overrides[(service, day)] = change == "1"
        return overrides

    def _load_trips(self) -> dict[str, Trip]:
        meta = {}
        for row in self._rows("trips.txt"):
            trip_id = (row.get("trip_id") or "").strip()
            service = row.get("service_id") or ""
            if not trip_id or trip_id in meta or not service:
                raise GTFSDataError("Missing or duplicate trip_id, or missing service_id in trips.txt")
            meta[trip_id] = (service, row.get("route_id") or "")
        by_trip: dict[str, list[StopCall]] = {t: [] for t in meta}
        for row in self._rows("stop_times.txt"):
            trip_id = row.get("trip_id") or ""
            stop_id = row.get("stop_id") or ""
            if trip_id not in by_trip or stop_id not in self.stops:
                raise GTFSDataError(f"Unknown trip/stop in stop_times: {trip_id!r} / {stop_id!r}")
            try:
                seq = int(row.get("stop_sequence") or "")
                arrival = seconds(row.get("arrival_time") or "")
                departure = seconds(row.get("departure_time") or "")
            except ValueError as exc:
                raise GTFSDataError(f"Invalid time or sequence in trip {trip_id!r}") from exc
            if arrival > departure:
                raise GTFSDataError(f"Arrival after departure in trip {trip_id!r}")
            # Only regular, non-request boarding/alighting is treated as guaranteed.
            by_trip[trip_id].append(StopCall(
                stop_id, arrival, departure, seq,
                row.get("pickup_type", "0") in ("", "0"),
                row.get("drop_off_type", "0") in ("", "0"),
            ))
        trips = {}
        for trip_id, (service, route) in meta.items():
            calls = sorted(by_trip[trip_id], key=lambda x: x.sequence)
            if len(calls) < 2:
                raise GTFSDataError(f"Trip {trip_id!r} has fewer than two timed stops")
            if len({c.sequence for c in calls}) != len(calls):
                raise GTFSDataError(f"Trip {trip_id!r} has duplicate stop_sequence")
            if any(a.departure > b.arrival for a, b in zip(calls, calls[1:])):
                raise GTFSDataError(f"Trip {trip_id!r} has non-monotonic times")
            trips[trip_id] = Trip(trip_id, service, route, tuple(calls))
        return trips

    def runs(self, service_id: str, on: date) -> bool:
        override = self.exceptions.get((service_id, on))
        if override is not None:
            return override
        pattern = self.calendar.get(service_id)
        return bool(pattern and pattern[0] <= on <= pattern[1] and pattern[2][on.weekday()])

    def connections(self, on: date, horizon: int = 172800) -> list[Connection]:
        """Generate connections across prior/current/next service dates.

        The queried calendar date is time zero. Trip IDs are unique per service date.
        """
        result = []
        for offset in (-1, 0, 1):
            day = on + timedelta(days=offset)
            base = offset * 86400
            for trip in self.trips.values():
                if not self.runs(trip.service_id, day):
                    continue
                instance = f"{trip.id}@{day.isoformat()}"
                for a, b in zip(trip.calls, trip.calls[1:]):
                    dep, arr = base + a.departure, base + b.arrival
                    if arr < 0 or dep > horizon:
                        continue
                    result.append(Connection(
                        instance, trip.id, trip.route_id, a.stop_id, b.stop_id,
                        dep, arr, a.pickup, b.dropoff,
                    ))
        result.sort(key=lambda c: (c.departure, c.arrival, c.instance_id))
        return result
