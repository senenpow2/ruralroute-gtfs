# Public roadmap

This is a candidate roadmap, **not** a claim that unbuilt features exist.

## 0.1 — initial offline engine

- [x] Read GTFS ZIP/folder
- [x] Calendar service exceptions
- [x] Service-day times past midnight
- [x] Multi-leg itinerary scanning
- [x] Configurable same-stop transfer buffers
- [x] Round-trip assessment and batch audit
- [x] JSON / CSV / terminal output
- [x] Synthetic example and regression tests

## 0.2 — important GTFS correctness gaps

- [ ] Parent station and platform transfer mapping
- [ ] `transfers.txt` minimum transfer times and prohibited connections
- [ ] Explicit DST regression testing and timezone semantics
- [ ] Detect/report unsupported feed constructs at load time
- [ ] `frequencies.txt` trips, including exact_times semantics

## 0.3 — accessibility and civic analysis

- [ ] Optional pedestrian network integration with transparent assumptions
- [ ] Wheelchair/station access filters without pretending unknown means accessible
- [ ] Sensitivity scoring by transfer buffer and service cancellation scenario
- [ ] GeoJSON stop-level return-gap export for mapping
- [ ] Reproducible documented audit against an approved public feed

## 1.0 — trusted integrations

- [ ] Public API stability contract and semantic versioning
- [ ] Published package / signed release artifacts
- [ ] Documented benchmark and memory-use budgets
- [ ] Maintainer governance, community issues, and at least one independent contributor
