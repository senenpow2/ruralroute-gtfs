# Architecture

```text
GTFS ZIP / folder
      │
      ▼
feed.py: validate supported tables, dates, timed calls
      │
      ▼
connections(service date -1 / 0 / +1): sorted stop-to-stop vehicle connections
      │
      ▼
planner.py: earliest arrival, state per (stop, vehicle count) and vehicle instance
      │
      ├── outbound: leave home after X, arrive at destination by Y
      └── inbound: leave destination after Z, be home by W
      │
      ▼
CLI: text, JSON or CSV assessments
```

### Why no mandatory dependencies?

Local councils, civic groups and researchers can run a single Python command
without a database, commercial geocoding service or secrets. The package has
no outbound network calls.

### Invariants

- GTFS time is a service-day offset and can exceed 24h.
- Trips are qualified by `trip_id@service_date`; the same GTFS trip_id on consecutive
  service days is never conflated.
- Boarding a new vehicle checks `pickup_type` and transfer buffer.
- Reaching a stop checks `drop_off_type`.
- Staying aboard a vehicle is not treated as a vehicle change.
- State is maintained per stop **and number of boarded vehicles**, so a later
  zero-transfer path cannot be suppressed by an earlier two-transfer one.
- A path beyond the maximum transfers is never returned.

### Extension points

The pure `earliest_arrival` and `assess_return` functions accept a precomputed
connection list. The CLI reuses it during a whole-feed audit. Additional data
sources, structured reports and optional routing services can build atop this
model without changing the user-facing JSON format unnecessarily.
