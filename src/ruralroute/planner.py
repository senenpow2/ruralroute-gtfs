"""Schedule-only connection scanning with trip continuity and transfer buffers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal

from .feed import Connection, Feed


@dataclass(frozen=True)
class Leg:
    trip_id: str
    route_id: str
    from_stop: str
    to_stop: str
    departure: int
    arrival: int


@dataclass(frozen=True)
class Journey:
    origin: str
    destination: str
    departure: int
    arrival: int
    legs: tuple[Leg, ...]

    def to_dict(self) -> dict:
        return {**asdict(self), "transfers": max(0, len(self.legs) - 1)}


@dataclass(frozen=True)
class ReturnAssessment:
    status: Literal["round_trip_found", "no_outbound", "no_return"]
    outbound: Journey | None
    inbound: Journey | None
    origin: str
    destination: str
    service_date: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "origin": self.origin,
            "destination": self.destination,
            "service_date": self.service_date,
            "outbound": self.outbound.to_dict() if self.outbound else None,
            "inbound": self.inbound.to_dict() if self.inbound else None,
            "interpretation": {
                "round_trip_found": "A scheduled round trip was found under the stated assumptions.",
                "no_outbound": "No supported scheduled outbound journey was found in the window.",
                "no_return": "An outbound journey exists, but no supported scheduled return was found.",
            }[self.status],
        }


def earliest_arrival(
    feed: Feed,
    on: date,
    origin: str,
    destination: str,
    depart_after: int,
    arrive_by: int,
    *,
    min_transfer: int = 300,
    max_transfers: int = 3,
    connections: list[Connection] | None = None,
) -> Journey | None:
    """Earliest supported arrival, with up to max_transfers vehicle changes.

    A rider may remain on a vehicle across adjacent GTFS stop pairs without
    incurring a transfer penalty. Boarding a *new* vehicle requires min_transfer.
    This optimizes arrival time, not price, reliability, accessibility or comfort.
    """
    if origin not in feed.stops or destination not in feed.stops:
        raise ValueError("Unknown origin or destination stop_id")
    if not (0 <= depart_after <= arrive_by <= 172800):
        raise ValueError("Expected 0 <= depart_after <= arrive_by <= 48 hours")
    if min_transfer < 0 or max_transfers < 0:
        raise ValueError("Transfer settings cannot be negative")
    if origin == destination:
        return Journey(origin, destination, depart_after, depart_after, ())

    # Keep one optimal label per (stop, number of vehicles), rather than one
    # label per stop. This prevents a faster, transfer-heavy path from hiding a
    # slightly slower path that still has enough transfers left to reach home.
    labels: dict[tuple[str, int], tuple[int, tuple[Leg, ...]]] = {
        (origin, 0): (depart_after, ()),
    }
    onboard: dict[tuple[str, int], tuple[str, int, tuple[Leg, ...]]] = {}
    best_dest: Journey | None = None
    stream = connections if connections is not None else feed.connections(on, horizon=arrive_by)

    for c in stream:
        if c.departure > arrive_by:
            break
        if c.arrival > arrive_by or c.departure < depart_after:
            continue

        for rides in range(1, max_transfers + 2):
            key = (c.instance_id, rides)
            state = onboard.get(key)
            known = labels.get((c.from_stop, rides - 1))
            if c.pickup and known:
                arrived, prior_legs = known
                buffer = 0 if rides == 1 else min_transfer
                if arrived + buffer <= c.departure and state is None:
                    state = (c.from_stop, c.departure, prior_legs)
                    onboard[key] = state
            if state is None or not c.dropoff:
                continue

            board_stop, board_time, prior_legs = state
            leg = Leg(c.trip_id, c.route_id, board_stop, c.to_stop, board_time, c.arrival)
            path = prior_legs + (leg,)
            label_key = (c.to_stop, rides)
            current = labels.get(label_key)
            if current is None or c.arrival < current[0]:
                labels[label_key] = (c.arrival, path)
            if c.to_stop == destination:
                candidate = Journey(origin, destination, path[0].departure, c.arrival, path)
                if (best_dest is None or candidate.arrival < best_dest.arrival or (
                    candidate.arrival == best_dest.arrival and len(path) < len(best_dest.legs)
                )):
                    best_dest = candidate

    return best_dest


def assess_return(
    feed: Feed,
    on: date,
    origin: str,
    destination: str,
    outbound_after: int,
    arrive_by: int,
    return_after: int,
    home_by: int,
    *,
    min_transfer: int = 300,
    max_transfers: int = 3,
    connections: list[Connection] | None = None,
) -> ReturnAssessment:
    """Identify whether the timetable contains outbound *and* return journeys.

    return_after is the earliest time the traveller can leave the destination.
    Dates/times are schedule-relative seconds and need not be on one civil day.
    """
    if not (0 <= outbound_after <= arrive_by <= return_after <= home_by <= 172800):
        raise ValueError("Expected ordered outbound/visit/return windows within 48 hours")
    stream = connections if connections is not None else feed.connections(on, horizon=home_by)
    outbound = earliest_arrival(
        feed, on, origin, destination, outbound_after, arrive_by,
        min_transfer=min_transfer, max_transfers=max_transfers, connections=stream,
    )
    if not outbound:
        return ReturnAssessment("no_outbound", None, None, origin, destination, str(on))
    inbound = earliest_arrival(
        feed, on, destination, origin, return_after, home_by,
        min_transfer=min_transfer, max_transfers=max_transfers, connections=stream,
    )
    status = "round_trip_found" if inbound else "no_return"
    return ReturnAssessment(status, outbound, inbound, origin, destination, str(on))
