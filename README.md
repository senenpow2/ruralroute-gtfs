# RuralRoute GTFS

**Find the journey home before you publish the journey out.**

[![CI](https://github.com/senenpow2/ruralroute-gtfs/actions/workflows/ci.yml/badge.svg)](https://github.com/senenpow2/ruralroute-gtfs/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

RuralRoute is a **free, offline, dependency-free transit timetable assessment tool**.
It examines [GTFS Schedule](https://gtfs.org/documentation/schedule/reference/) data to answer a simple but neglected question:

> *If someone takes public transport to an appointment, job or event, is there a scheduled journey home afterwards?*

Built for rural communities, local authorities, transport advocates, researchers,
accessible event organisers and trip-planning applications. Runs with **no API key**, no
paid routing service, no location tracking and no cloud backend. It is not a replacement
for a live journey planner.

## What exists in v0.1.0

- Reads GTFS Schedule feeds from a directory or ZIP file.
- Understands calendar.txt and calendar_dates.txt, including added/removed services.
- Understands service-day times beyond midnight (`25:10:00`).
- Searches chains of **multiple scheduled vehicles** with configurable transfer buffers.
- Distinguishes `round_trip_found`, `no_outbound` and `no_return`.
- Checks a single destination (`check`) or many (`audit`).
- Exports human-readable text, machine-readable JSON, CSV or a **standalone HTML dashboard**.
- Uses only Python's standard library at runtime.
- Ships a **clearly synthetic** example feed and automated unit tests.

## Installation

Clone this repository, then from its root:

```bash
python -m pip install -e .
```

Or without installation:

```bash
PYTHONPATH=src python -m ruralroute --help
```

## Quick start (fictional demonstration)

The demo is **made-up service data**, not real bus times in Wales.

```bash
ruralroute stops --feed examples/synthetic-wales

# Appointment: an outbound AND a return home both exist.
ruralroute check --feed examples/synthetic-wales \
  --date 2026-11-04 --from HOME --to HOSP \
  --outbound-after 08:00 --arrive-by 12:00 \
  --return-after 16:00 --home-by 23:00

# Evening event: you can get there, but this feed has no return after 18:00.
ruralroute check --feed examples/synthetic-wales \
  --date 2026-11-04 --from HOME --to VENUE \
  --outbound-after 08:00 --arrive-by 12:00 \
  --return-after 18:00 --home-by 23:00 --format json

# Audit every other stop in a feed; export results for a council report.
ruralroute audit --feed path/to/your-gtfs.zip \
  --date 2026-11-04 --from YOUR_STOP_ID \
  --outbound-after 08:00 --arrive-by 12:00 \
  --return-after 18:00 --home-by 23:30 --format csv > gaps.csv

# Share an offline, print-friendly HTML report with council or campaign colleagues.
ruralroute audit --feed path/to/your-gtfs.zip \
  --date 2026-11-04 --from YOUR_STOP_ID \
  --return-after 18:00 --format html > report.html
```

The timetable's `stop_id` identifiers are **not** necessarily names. Use `stops --filter town`
to locate one. `--min-transfer` defaults to 5 minutes; `--max-transfers` defaults to 3.
Times are on the agency's GTFS service-day clock: `--home-by 01:00` after a later
`--return-after` means the following day. You may also write `25:00` explicitly.

## Example result

```text
Example Village → Example Hospital | 2026-11-04
Status: ROUND TRIP FOUND
Outbound: 08:00 → 09:10 (2 vehicle(s))
  Example Village 08:00 → Example Town Centre 08:50 [V1]
  Example Town Centre 09:00 → Example Hospital 09:10 [C2]
Return: 16:50 → 18:20 (2 vehicle(s))
  Example Hospital 16:50 → Example Town Centre 17:00 [C2]
  Example Town Centre 17:30 → Example Village 18:20 [V1]
```

## How it works

The tool parses scheduled stop-to-stop connections, selects GTFS services operating on
the chosen date (including nearby service dates for after-midnight trips), and scans
connections in chronological order. It tracks whether the traveller is **already on the
same vehicle**, so staying aboard does not count as a transfer. Each stop retains the
best time by number of boarded vehicles; this avoids discarding feasible low-transfer
journeys merely because a faster route uses too many changes.

Checks are deterministic: a feed, a date, IDs, and time windows produce the same answer.
Results are designed to be embedded in dashboards, council research or other open-source apps.

## Important safety and accuracy limits

**`round_trip_found` is not a guarantee that a person can travel.** A static timetable may
be wrong, a service cancelled, a connection missed or a stop inaccessible. **`no_return`
means none was found in the supplied feed and query window, not that none exists in reality.**

Supported: static, explicitly timed, regularly boarding GTFS trips; weekly calendars,
date exceptions, >24h times; same-stop transfers. Unsupported in v0.1: live vehicle data,
fares, demand-responsive/flex journeys, `frequencies.txt`, pedestrian paths, stop hierarchy,
station transfer rules, wheelchair access and holiday-specific data not supplied by the feed.
The engine does not model DST transition semantics or time-zone crossings. See
[limitations](docs/LIMITATIONS.md) before using results for a real journey.

## Why an open source project?

A transport campaign group should be able to show evidence of **return-trip gaps**
without a commercial API subscription, storing passenger location, or building an
entire routing platform. RuralRoute is one small, independently reusable building block.

Please help maintain it: file reproductions against **publicly redistributable** data,
add tests for tricky service-day cases, improve documentation and suggest new formats.
See [Contributing](CONTRIBUTING.md), [Roadmap](docs/ROADMAP.md), [Security](SECURITY.md)
and [Architecture](docs/ARCHITECTURE.md).

## Developing

```bash
python -m pip install -e . pytest ruff
python -m pytest -q
ruff check src tests
```

## License

MIT for code and the fictional example. GTFS feeds from actual transport operators
have their own licenses: do not redistribute a real feed unless its license permits it.
