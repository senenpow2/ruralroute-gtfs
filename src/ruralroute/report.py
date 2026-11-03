"""Accessible, fully standalone HTML reports: no CDN, JS, cookies or tracking."""

from __future__ import annotations

from collections import Counter
from html import escape

from .feed import Feed
from .planner import ReturnAssessment


def _clock(value: int | None) -> str:
    if value is None:
        return "—"
    day, rest = divmod(value, 86400)
    h, rest = divmod(rest, 3600)
    m = rest // 60
    return f"{h:02d}:{m:02d}" + (f" (+{day}d)" if day else "")


def render_html(feed: Feed, results: list[ReturnAssessment], title: str = "RuralRoute audit") -> str:
    """Generate static HTML from computed, not asserted, timetable results."""
    counts = Counter(r.status for r in results)
    safe_title = escape(title)
    lines = []
    for r in results:
        status = r.status.replace("_", " ").title()
        outbound = _clock(r.outbound.arrival if r.outbound else None)
        inbound = _clock(r.inbound.arrival if r.inbound else None)
        outbound_path = " → ".join(escape(feed.stops[leg.to_stop].name) for leg in r.outbound.legs) if r.outbound else "—"
        inbound_path = " → ".join(escape(feed.stops[leg.to_stop].name) for leg in r.inbound.legs) if r.inbound else "—"
        lines.append(
            f'<tr><td><strong>{escape(feed.stops[r.destination].name)}</strong>'
            f'<small>{escape(r.destination)}</small></td>'
            f'<td><span class="tag {escape(r.status)}">{escape(status)}</span></td>'
            f'<td>{outbound}<small>{outbound_path}</small></td>'
            f'<td>{inbound}<small>{inbound_path}</small></td></tr>'
        )
    date_text = escape(results[0].service_date) if results else "No date"
    home = escape(feed.stops[results[0].origin].name) if results else "No origin"
    cards = "".join(
        f'<div class="metric"><div class="number">{counts[key]}</div><div class="name">{label}</div></div>'
        for key, label in (
            ("round_trip_found", "Scheduled returns found"),
            ("no_outbound", "No outbound found"),
            ("no_return", "No return found"),
        )
    )
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{safe_title} — RuralRoute</title>
<style>
:root {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; line-height:1.5;
  color:#172733; background:#f5f7f8; }}
body {{ max-width:1100px; margin:0 auto; padding:clamp(16px,4vw,48px); }}
header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:12px; justify-content:space-between; }}
h1 {{ font-size:clamp(1.8rem,4vw,2.7rem); margin:.2em 0; letter-spacing:-.03em; }}
.brand {{ font-size:.85rem; font-weight:800; color:#116466; letter-spacing:.12em; }}
.sub {{ color:#435968; margin-top:0; }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:26px 0; }}
.metric {{ padding:22px; border-radius:12px; background:#fff; border:1px solid #dce5e7; }}
.number {{ font-size:2.2rem; line-height:1.1; font-weight:750; font-variant-numeric:tabular-nums; }}
.name {{ font-size:.85rem; color:#506570; margin-top:5px; }}
.panel {{ border:1px solid #dce5e7; border-radius:12px; background:white; overflow-x:auto; }}
table {{ width:100%; min-width:660px; border-collapse:collapse; font-size:.93rem; }}
th {{ text-align:left; font-size:.74rem; color:#546978; background:#ecf2f3; letter-spacing:.04em; text-transform:uppercase; }}
td,th {{ padding:16px; border-bottom:1px solid #e5ecee; vertical-align:top; }}
tr:last-child td {{ border-bottom:0; }}
small {{ display:block; color:#5e717d; font-size:.75rem; margin-top:4px; max-width:35ch; }}
.tag {{ display:inline-block; border-radius:18px; padding:3px 9px; font-size:.8rem; font-weight:650; white-space:nowrap; }}
.round_trip_found {{ background:#dff5ed; color:#165b43; }}
.no_return {{ background:#fcebd6; color:#89511f; }}
.no_outbound {{ background:#e8ebef; color:#3c5161; }}
.warning {{ border-left:4px solid #ba7a2e; padding:14px 18px; background:#fff5e7; margin:26px 0; }}
footer {{ color:#5c6d78; font-size:.82rem; margin-top:25px; }}
@media (prefers-color-scheme:dark) {{
 :root {{ color:#eaf0f1; background:#111c22; }} .sub,footer,small,.name {{color:#b4c6cb;}}
 .panel,.metric {{ background:#1a2930; border-color:#344a55; }}
 td,th {{border-color:#344a55;}} th {{background:#253b44; color:#d3e0e4;}}
 .warning {{background:#44331f; color:#ffe8c3;}} .brand {{color:#91d6c9;}}
}}
@media print {{ :root {{color:#000; background:#fff;}} .metric,.panel {{border-color:#888;}} body {{padding:4mm;}} }}
</style>
</head>
<body>
<header><div class="brand">RURALROUTE / GTFS</div><div>Offline timetable assessment</div></header>
<main>
<h1>{safe_title}</h1>
<p class="sub">From <strong>{home}</strong> · GTFS service day <strong>{date_text}</strong> · {len(results)} destination(s)</p>
<section class="metrics" aria-label="Summary">{cards}</section>
<section aria-labelledby="results-heading"><h2 id="results-heading">Destination assessment</h2>
<div class="panel"><table><thead><tr><th scope="col">Destination</th><th scope="col">Schedule result</th>
<th scope="col">Outbound arrival</th><th scope="col">Home arrival</th></tr></thead>
<tbody>{''.join(lines) or '<tr><td colspan="4">No destinations checked</td></tr>'}</tbody></table></div></section>
<section class="warning" role="note"><strong>Read before using:</strong> These are <em>scheduled</em> results from a supplied
GTFS feed. They do not confirm real-time running, safety, wheelchair accessibility, fares,
walking connections or cancellations. “No return found” does not prove that no service exists.</section>
</main>
<footer>Generated locally with RuralRoute GTFS · No tracking, external scripts or network requests.</footer>
</body>
</html>'''
