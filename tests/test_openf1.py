"""Unit-level validation for OpenF1 source mapping and non-leaky temporal joins."""
from __future__ import annotations

from apex_f1.openf1_import import build_openf1_history


def test_completion_and_position_join_uses_only_observed_events():
    session = "2024-03-02T15:00:00+00:00"
    rows = [
        # lap 1 lacks duration; use same driver's next lap start as end
        {"driver_number": 1, "lap_number": 1,
         "date_start": "2024-03-02T15:00:10+00:00", "lap_duration": None},
        {"driver_number": 1, "lap_number": 2,
         "date_start": "2024-03-02T15:01:40+00:00", "lap_duration": 90.0},
        {"driver_number": 2, "lap_number": 1,
         "date_start": "2024-03-02T15:00:11+00:00", "lap_duration": None},
        {"driver_number": 2, "lap_number": 2,
         "date_start": "2024-03-02T15:01:43+00:00", "lap_duration": 95.0},
    ]
    race = build_openf1_history(
        year=2024, round_number=1, session_start=session, laps=rows,
        drivers=[{"driver_number": 1, "name_acronym": "AAA"},
                 {"driver_number": 2, "name_acronym": "BBB"}],
        stints=[
            {"driver_number": 1, "lap_start": 1, "compound": "SOFT",
             "stint_number": 1, "tyre_age_at_start": 0, "lap_end": 3},
            {"driver_number": 2, "lap_start": 1, "compound": "HARD",
             "stint_number": 1, "tyre_age_at_start": 1, "lap_end": 1},
            {"driver_number": 2, "lap_start": 2, "compound": "MEDIUM",
             "stint_number": 2, "tyre_age_at_start": 0, "lap_end": 25},
        ],
        pits=[
            {"driver_number": 2, "lap_number": 2, "date": "2024-03-02T15:03:20+00:00"},
        ],
        positions=[
            {"driver_number": 1, "position": 1, "date": "2024-03-02T15:01:00+00:00"},
            {"driver_number": 2, "position": 2, "date": "2024-03-02T15:01:00+00:00"},
            {"driver_number": 2, "position": 1, "date": "2024-03-02T15:03:10+00:00"},
        ],
    )
    lap1 = race.snapshot(1)
    assert lap1["cutoff_session_seconds"] == 100.0
    assert {x["driver"] for x in lap1["drivers"]} == {"AAA"}
    lap2 = race.snapshot(2)
    aaa = next(x for x in lap2["drivers"] if x["driver"] == "AAA")
    bbb = next(x for x in lap2["drivers"] if x["driver"] == "BBB")
    assert lap2["cutoff_session_seconds"] == 190.0
    assert aaa["last_completed_lap"] == 2
    assert aaa["last_reported_position"] == 1
    assert bbb["last_completed_lap"] == 1
    assert bbb["last_known_compound"] == "HARD"
    assert bbb["last_reported_position"] == 2
    assert bbb["observed_pit_ins"] == 0


def test_tyre_stint_future_changes_not_exposed_early():
    data = build_openf1_history(
        year=2024, round_number=1, session_start="2024-03-02T15:00:00Z",
        laps=[{"driver_number": 12, "lap_number": 1, "date_start":
               "2024-03-02T15:00:05Z", "lap_duration": 95.0},
              {"driver_number": 12, "lap_number": 2, "date_start":
               "2024-03-02T15:01:40Z", "lap_duration": 96.0}],
        drivers=[], stints=[
            {"driver_number": 12, "lap_start": 1, "compound": "HARD",
             "stint_number": 1, "tyre_age_at_start": 1},
            {"driver_number": 12, "lap_start": 2, "compound": "SOFT",
             "stint_number": 2, "tyre_age_at_start": 0}],
        pits=[], positions=[],
    )
    assert data.source.startswith("OpenF1")
    assert data.snapshot(1)["drivers"][0]["last_known_compound"] == "HARD"
    assert data.snapshot(2)["drivers"][0]["last_known_compound"] == "SOFT"


def test_pit_passage_is_not_revealed_before_its_utc_timestamp():
    """A pit event tagged lap 1 but occurring after lap 1 must wait until lap 2."""
    history = build_openf1_history(
        year=2024,
        round_number=4,
        session_start="2024-04-07T06:00:00Z",
        laps=[
            {"driver_number": 7, "lap_number": 1,
             "date_start": "2024-04-07T06:00:00Z", "lap_duration": 90.0},
            {"driver_number": 7, "lap_number": 2,
             "date_start": "2024-04-07T06:01:30Z", "lap_duration": 90.0},
            {"driver_number": 7, "lap_number": 3,
             "date_start": "2024-04-07T06:03:00Z", "lap_duration": 90.0},
        ],
        drivers=[{"driver_number": 7, "name_acronym": "AAA"}],
        stints=[], positions=[],
        pits=[{"driver_number": 7, "lap_number": 1,
               "date": "2024-04-07T06:01:35Z"}],
    )
    assert history.snapshot(1)["drivers"][0]["pit_in_on_last_lap"] is False
    assert history.snapshot(1)["drivers"][0]["observed_pit_ins"] == 0
    assert history.snapshot(2)["drivers"][0]["pit_in_on_last_lap"] is True
    assert history.snapshot(2)["drivers"][0]["observed_pit_ins"] == 1
    assert history.snapshot(3)["drivers"][0]["observed_pit_ins"] == 1
