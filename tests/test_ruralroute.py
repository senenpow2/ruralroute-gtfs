"""Behavioural tests use a known, synthetic, distributable feed."""

from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

import pytest

from ruralroute.cli import main
from ruralroute.feed import Feed, GTFSDataError, seconds
from ruralroute.planner import assess_return, earliest_arrival

DEMO = Path(__file__).parent.parent / "examples" / "synthetic-wales"
DAY = date(2026, 11, 4)


def fixture_copy(tmp_path, changes=None):
    target = tmp_path / "feed"
    shutil.copytree(DEMO, target)
    for filename, rows in (changes or {}).items():
        with (target / filename).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return target


def test_gtfs_hours_over_24_and_invalid():
    assert seconds("25:05:30") == 90330
    assert seconds("8:00") == 28800
    for bad in ("-01:00", "12:60", "abc", "13:01:99", "100:00", "1", "1:2:3:4"):
        with pytest.raises(GTFSDataError):
            seconds(bad)


def test_demo_two_vehicle_outbound_with_return():
    feed = Feed(DEMO)
    a = assess_return(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600, 16*3600, 23*3600)
    assert a.status == "round_trip_found"
    assert [x.trip_id for x in a.outbound.legs] == ["village_in", "hospital_out"]
    assert [x.trip_id for x in a.inbound.legs] == ["hospital_back", "village_out_early"]
    assert a.outbound.arrival == 9*3600+10*60
    assert a.inbound.arrival == 18*3600+20*60
    assert a.to_dict()["outbound"]["transfers"] == 1


def test_venue_is_stranding_risk_in_evening_window():
    assessment = assess_return(Feed(DEMO), DAY, "HOME", "VENUE", 8*3600, 12*3600, 18*3600, 23*3600)
    assert assessment.status == "no_return"
    assert assessment.outbound is not None
    assert assessment.inbound is None


def test_no_outbound_if_too_late():
    assessment = assess_return(Feed(DEMO), DAY, "HOME", "HOSP", 10*3600, 12*3600, 16*3600, 23*3600)
    assert assessment.status == "no_outbound"


def test_transfer_buffer():
    feed = Feed(DEMO)
    assert earliest_arrival(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600, min_transfer=600)
    assert earliest_arrival(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600, min_transfer=601) is None


def test_transfer_limit():
    feed = Feed(DEMO)
    assert earliest_arrival(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600, max_transfers=1)
    assert earliest_arrival(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600, max_transfers=0) is None


def test_stay_on_vehicle_across_multiple_connections(tmp_path):
    feedpath = fixture_copy(tmp_path)
    with (feedpath / "trips.txt").open("a") as f:
        f.write("V1,DAILY,three_stops\n")
    with (feedpath / "stop_times.txt").open("a") as f:
        f.write("three_stops,10:00:00,10:00:00,HOME,1\n")
        f.write("three_stops,10:30:00,10:35:00,TOWN,2\n")
        f.write("three_stops,10:45:00,10:45:00,HOSP,3\n")
    journey = earliest_arrival(Feed(feedpath), DAY, "HOME", "HOSP", 9*3600, 12*3600, max_transfers=0)
    assert journey is not None
    assert len(journey.legs) == 1
    assert journey.legs[0].arrival == 10*3600+45*60


def test_calendar_date_cancellation_and_extra_day(tmp_path):
    feedpath = fixture_copy(tmp_path)
    (feedpath / "calendar_dates.txt").write_text(
        "service_id,date,exception_type\nDAILY,20261104,2\nDAILY,20261105,1\n", encoding="utf-8"
    )
    feed = Feed(feedpath)
    assert not feed.runs("DAILY", DAY)
    assert feed.runs("DAILY", date(2026, 11, 5))
    assert earliest_arrival(feed, DAY, "HOME", "HOSP", 8*3600, 12*3600) is None


def test_calendar_dates_only(tmp_path):
    feedpath = fixture_copy(tmp_path)
    (feedpath / "calendar.txt").unlink()
    (feedpath / "calendar_dates.txt").write_text(
        "service_id,date,exception_type\nDAILY,20261104,1\n", encoding="utf-8"
    )
    feed = Feed(feedpath)
    assert feed.runs("DAILY", DAY)
    assert not feed.runs("DAILY", date(2026, 11, 3))


def test_pickup_and_dropoff_restrictions(tmp_path):
    feedpath = fixture_copy(tmp_path)
    rows = list(csv.DictReader((feedpath / "stop_times.txt").open()))
    rows[0]["pickup_type"] = "1"
    with (feedpath / "stop_times.txt").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[*rows[0], "pickup_type"])
        w.writeheader()
        w.writerows(rows)
    assert earliest_arrival(Feed(feedpath), DAY, "HOME", "TOWN", 8*3600, 12*3600) is None


def test_zip_support(tmp_path):
    zip_path = tmp_path / "feed.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in DEMO.iterdir():
            z.write(f, f.name)
    feed = Feed(zip_path)
    assert "HOME" in feed.stops
    assert len(feed.connections(DAY)) > 0


def test_missing_feed_file_is_reported(tmp_path):
    path = fixture_copy(tmp_path)
    (path / "stop_times.txt").unlink()
    with pytest.raises(GTFSDataError, match="stop_times.txt"):
        Feed(path)


def test_non_monotonic_trip_rejected(tmp_path):
    path = fixture_copy(tmp_path)
    text = (path / "stop_times.txt").read_text()
    (path / "stop_times.txt").write_text(text.replace("08:50:00,08:50:00,TOWN", "07:50:00,07:50:00,TOWN"))
    with pytest.raises(GTFSDataError, match="non-monotonic"):
        Feed(path)


def test_cli_json_and_csv(capsys):
    opts = ["check", "--feed", str(DEMO), "--date", "2026-11-04", "--from", "HOME", "--to", "VENUE", "--return-after", "18:00", "--format", "json"]
    assert main(opts) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["results"][0]["status"] == "no_return"
    audit = ["audit", "--feed", str(DEMO), "--date", "2026-11-04", "--from", "HOME", "--limit", "2", "--format", "csv"]
    assert main(audit) == 0
    assert len(list(csv.reader(io.StringIO(capsys.readouterr().out)))) == 3


def test_cli_windows_roll_over_midnight():
    from argparse import Namespace
    from ruralroute.cli import _windows
    args = Namespace(outbound_after=20*3600, arrive_by=23*3600, return_after=25*3600,
                     home_by=2*3600)
    assert _windows(args) == (72000, 82800, 90000, 93600)


def test_unknown_stop_reported(capsys):
    assert main(["check", "--feed", str(DEMO), "--date", "2026-11-04", "--from", "FAKE", "--to", "HOME"]) == 2
    assert "Unknown origin" in capsys.readouterr().err


def test_after_midnight_gtfs_trip(tmp_path):
    path = fixture_copy(tmp_path)
    with (path / "trips.txt").open("a") as f:
        f.write("V1,DAILY,night\n")
    with (path / "stop_times.txt").open("a") as f:
        f.write("night,24:10:00,24:10:00,HOME,1\n")
        f.write("night,25:10:00,25:10:00,TOWN,2\n")
    journey = earliest_arrival(Feed(path), DAY, "HOME", "TOWN", 24*3600, 26*3600)
    assert journey is not None
    assert journey.departure == 24*3600+10*60
    assert journey.arrival == 25*3600+10*60


def test_maximum_transfer_labels_not_pruned(tmp_path):
    """Faster arrival with more transfers must not hide a feasible later direct arrival."""
    path = fixture_copy(tmp_path)
    with (path / "trips.txt").open("a") as f:
        f.write("C2,DAILY,fast_first\nC2,DAILY,fast_second\nC2,DAILY,slow_direct\nC2,DAILY,finish\n")
    with (path / "stop_times.txt").open("a") as f:
        f.write("fast_first,10:00:00,10:00:00,HOME,1\nfast_first,10:05:00,10:05:00,VENUE,2\n")
        f.write("fast_second,10:05:00,10:05:00,VENUE,1\nfast_second,10:10:00,10:10:00,TOWN,2\n")
        f.write("slow_direct,10:00:00,10:00:00,HOME,1\nslow_direct,10:30:00,10:30:00,TOWN,2\n")
        f.write("finish,10:40:00,10:40:00,TOWN,1\nfinish,11:00:00,11:00:00,HOSP,2\n")
    # One transfer allowed; direct+finish must remain discoverable.
    journey = earliest_arrival(Feed(path), DAY, "HOME", "HOSP", 9*3600, 12*3600,
                              min_transfer=0, max_transfers=1)
    assert journey is not None
    assert [leg.trip_id for leg in journey.legs] == ["slow_direct", "finish"]


def test_html_report_is_standalone_and_escapes_feed_text(tmp_path, capsys):
    path = fixture_copy(tmp_path)
    stops = (path / "stops.txt").read_text().replace("Example Evening Venue", "<script>alert(1)</script>")
    (path / "stops.txt").write_text(stops)
    from ruralroute.report import render_html
    feed = Feed(path)
    result = assess_return(feed, DAY, "HOME", "VENUE", 8*3600, 12*3600, 18*3600, 23*3600)
    report = render_html(feed, [result])
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
    assert "<script>alert(1)</script>" not in report
    assert '<meta charset="utf-8">' in report
    assert "No return found" in report
    assert main(["check", "--feed", str(path), "--date", "2026-11-04", "--from", "HOME", "--to", "VENUE", "--format", "html"]) == 0
    assert "<!doctype html>" in capsys.readouterr().out


def test_previous_day_over_midnight_service_is_visible(tmp_path):
    path = fixture_copy(tmp_path)
    with (path / "trips.txt").open("a") as f:
        f.write("V1,DAILY,yesterday_late\n")
    with (path / "stop_times.txt").open("a") as f:
        f.write("yesterday_late,24:30:00,24:30:00,HOME,1\n")
        f.write("yesterday_late,25:00:00,25:00:00,TOWN,2\n")
    # On 4 November at 00:30, the 3 November 24:30 GTFS service is reachable.
    pathfeed = Feed(path)
    journey = earliest_arrival(pathfeed, DAY, "HOME", "TOWN", 30*60, 2*3600)
    assert journey is not None
    assert journey.departure == 30*60
    assert journey.arrival == 3600


def test_negative_and_unknown_settings_rejected():
    feed = Feed(DEMO)
    with pytest.raises(ValueError, match="cannot be negative"):
        earliest_arrival(feed, DAY, "HOME", "HOSP", 0, 10*3600, min_transfer=-1)
    with pytest.raises(ValueError, match="Unknown"):
        earliest_arrival(feed, DAY, "HOME", "INVALID", 0, 10*3600)


def test_no_artificial_walk_between_distinct_stop_ids():
    feed = Feed(DEMO)
    # Same timetable, but no pedestrian/nearby-stop assumptions are invented.
    assert earliest_arrival(feed, DAY, "VENUE", "HOSP", 9*3600, 12*3600) is None
