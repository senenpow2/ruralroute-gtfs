# Honest limitations (v0.1)

RuralRoute is an **experimental feasibility-assessment engine for schedule data**, not
an approved passenger itinerary system. The only reliable meaning of `no_return` is
"no supported schedule path found in *this feed*, with *these parameters*."

- Real-time delays, cancellations and strikes are not integrated.
- `frequencies.txt`, flexible/demand-responsive trips, non-timed stop_times, and
  location-based pick-up are not supported. If a feed relies on these features,
  results will be incomplete; use the official operator's planner.
- Changing stops requires the *identical stop ID*. There is currently no walking
  transfer, station parent-child mapping, or transfers.txt constraint handling.
- Wheelchair boarding, step-free transfers, lighting, personal safety, fares and
  seat availability are not assessed.
- Service times are GTFS agency-local wall-clock schedule seconds. UTC offsets,
  DST fallbacks and cross-timezone feeds are not fully resolved.
- A path is earliest-arrival among supported connections and transfer constraints.
  It is **not** the most reliable, cheapest or most accessible path.
- `calendar_dates.txt` removes/adds service *only when listed in the feed*.
  Incomplete feeds may omit holiday arrangements.
- A static feed is a snapshot; no freshness guarantee exists. Compare dates and
  confirm actual travel with operators.
- Very large feeds are held in memory; batch audits rescan connections by stop.
  Consider limiting audit scope and monitoring memory use.
- No GTFS official certification is claimed. This is a deliberately narrow parser.

## Responsible use

Use findings as **leads for further investigation**. Verify with official service
information before advising passengers. Never publish inferred personal travel
patterns or imply the presence/absence of service without identifying the feed,
calendar date, service hours and algorithm restrictions.
