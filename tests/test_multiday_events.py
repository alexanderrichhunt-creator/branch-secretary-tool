"""Multi-day branch events: optional end date, validation, and calendar span."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_DB.close()
os.environ["DATABASE_URL"] = "sqlite:///" + _DB.name
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INIT_ADMIN_EMAIL"] = "admin@example.com"
os.environ["INIT_ADMIN_PASSWORD"] = "test-password-123"

from app import create_app, db  # noqa: E402
from app.event_utils import (  # noqa: E402
    event_duration,
    event_inclusive_end_date,
    iter_event_occurrences,
    occurrence_inclusive_end,
    occurrence_is_multiday,
    resolve_event_range,
)
from app.models import Event  # noqa: E402
from app.routes import _parse_event_times_from_form  # noqa: E402


def _event(**kwargs):
    defaults = dict(
        starts_at=datetime(2027, 6, 14, 0, 0),
        end_at=datetime(2027, 6, 15, 0, 0),
        all_day=True,
        recurrence_freq=None,
        recurrence_interval=1,
        recurrence_byweekday=None,
        recurrence_until=None,
        recurrence_bysetpos=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class ResolveRangeTests(unittest.TestCase):
    def test_blank_end_date_defaults_to_start_for_all_day(self):
        starts, ends, err = resolve_event_range(date(2027, 6, 14), None, all_day=True)
        self.assertIsNone(err)
        self.assertEqual(starts, datetime(2027, 6, 14))
        # Exclusive end, same shape as existing single-day rows.
        self.assertEqual(ends, datetime(2027, 6, 15))
        self.assertEqual(event_inclusive_end_date(_event(starts_at=starts, end_at=ends, all_day=True)), date(2027, 6, 14))

    def test_multi_day_all_day_is_inclusive(self):
        starts, ends, err = resolve_event_range(date(2027, 6, 28), date(2027, 7, 2), all_day=True)
        self.assertIsNone(err)
        self.assertEqual(starts, datetime(2027, 6, 28))
        self.assertEqual(ends, datetime(2027, 7, 3))
        event = _event(starts_at=starts, end_at=ends, all_day=True)
        self.assertEqual(event_inclusive_end_date(event), date(2027, 7, 2))
        self.assertEqual(event_duration(event), timedelta(days=5))

    def test_end_before_start_is_rejected(self):
        starts, ends, err = resolve_event_range(date(2027, 6, 18), date(2027, 6, 14), all_day=True)
        self.assertIsNone(starts)
        self.assertIsNone(ends)
        self.assertEqual(err, "End date must be on or after the start date.")

    def test_timed_same_day_keeps_clock_times(self):
        starts, ends, err = resolve_event_range(
            date(2027, 6, 14),
            date(2027, 6, 14),
            all_day=False,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        self.assertIsNone(err)
        self.assertEqual(starts, datetime(2027, 6, 14, 9, 0))
        self.assertEqual(ends, datetime(2027, 6, 14, 10, 0))
        self.assertFalse(occurrence_is_multiday(starts, ends, False))

    def test_timed_overnight_still_rolls_forward(self):
        starts, ends, err = resolve_event_range(
            date(2027, 6, 14),
            None,
            all_day=False,
            start_time=time(21, 0),
            end_time=time(6, 0),
        )
        self.assertIsNone(err)
        self.assertEqual(ends, datetime(2027, 6, 15, 6, 0))

    def test_timed_span_uses_later_end_date(self):
        starts, ends, err = resolve_event_range(
            date(2027, 6, 14),
            date(2027, 6, 16),
            all_day=False,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.assertIsNone(err)
        self.assertEqual(ends, datetime(2027, 6, 16, 17, 0))
        self.assertTrue(occurrence_is_multiday(starts, ends, False))
        self.assertEqual(occurrence_inclusive_end(starts, ends, False), date(2027, 6, 16))


class OccurrenceWindowTests(unittest.TestCase):
    def test_single_day_all_day_duration_unchanged(self):
        event = _event()
        self.assertEqual(event_duration(event), timedelta(days=1))
        found = list(
            iter_event_occurrences(
                event,
                datetime(2027, 6, 1),
                datetime(2027, 7, 1),
            )
        )
        self.assertEqual(found, [(datetime(2027, 6, 14), datetime(2027, 6, 15))])

    def test_multi_day_crosses_month_boundary(self):
        event = _event(
            starts_at=datetime(2027, 6, 28),
            end_at=datetime(2027, 7, 3),
            all_day=True,
        )
        june = list(iter_event_occurrences(event, datetime(2027, 6, 1), datetime(2027, 7, 1)))
        july = list(iter_event_occurrences(event, datetime(2027, 7, 1), datetime(2027, 8, 1)))
        self.assertEqual(len(june), 1)
        self.assertEqual(june[0][0], datetime(2027, 6, 28))
        self.assertEqual(june[0][1], datetime(2027, 7, 3))
        # Starts in June, but July's fetch still receives the same span.
        self.assertEqual(july, june)
        self.assertTrue(occurrence_is_multiday(*june[0], True))

    def test_event_outside_the_window_is_omitted(self):
        event = _event()
        found = list(iter_event_occurrences(event, datetime(2027, 7, 1), datetime(2027, 8, 1)))
        self.assertEqual(found, [])

    def test_recurring_multi_day_includes_overlap_from_previous_month(self):
        # Friday through the following Friday, so the June 25 occurrence
        # still covers July 1–2 and must show up in July's fetch.
        event = _event(
            starts_at=datetime(2027, 6, 25),
            end_at=datetime(2027, 7, 3),
            all_day=True,
            recurrence_freq="weekly",
            recurrence_interval=1,
            recurrence_byweekday="FR",
        )
        july = list(iter_event_occurrences(event, datetime(2027, 7, 1), datetime(2027, 8, 1)))
        starts = [occ[0].date() for occ in july]
        self.assertIn(date(2027, 6, 25), starts)
        self.assertIn(date(2027, 7, 2), starts)
        june_tail = next(occ for occ in july if occ[0].date() == date(2027, 6, 25))
        self.assertEqual(occurrence_inclusive_end(*june_tail, True), date(2027, 7, 2))


class EventFormAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        with self.app.app_context():
            Event.query.delete()
            db.session.commit()
        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "test-password-123"},
            follow_redirects=True,
        )

    def test_form_parser_defaults_and_rejects(self):
        with self.app.test_request_context(
            "/events/add",
            method="POST",
            data={"event_date": "2027-06-14", "all_day": "1"},
        ):
            starts, ends, all_day, err = _parse_event_times_from_form()
        self.assertIsNone(err)
        self.assertTrue(all_day)
        self.assertEqual(starts, datetime(2027, 6, 14))
        self.assertEqual(ends, datetime(2027, 6, 15))

        with self.app.test_request_context(
            "/events/add",
            method="POST",
            data={
                "event_date": "2027-06-18",
                "event_end_date": "2027-06-14",
                "all_day": "1",
            },
        ):
            _starts, _ends, _all_day, err = _parse_event_times_from_form()
        self.assertEqual(err, "End date must be on or after the start date.")

    def test_api_spans_every_day_across_the_month_boundary(self):
        response = self.client.post(
            "/events/add",
            data={
                "title": "Nauvoo Trip",
                "event_date": "2027-06-28",
                "event_end_date": "2027-07-02",
                "all_day": "1",
                "category": "branch",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

        june = self.client.get("/api/events?start=2027-06-01T00:00:00&end=2027-07-01T00:00:00")
        july = self.client.get("/api/events?start=2027-07-01T00:00:00&end=2027-08-01T00:00:00")
        self.assertEqual(june.status_code, 200)
        june_events = [item for item in june.get_json() if item["extendedProps"]["fullTitle"] == "Nauvoo Trip"]
        july_events = [item for item in july.get_json() if item["extendedProps"]["fullTitle"] == "Nauvoo Trip"]
        self.assertEqual(len(june_events), 1)
        self.assertEqual(june_events[0]["start"], "2027-06-28")
        self.assertEqual(june_events[0]["end"], "2027-07-03")
        self.assertTrue(june_events[0]["allDay"])
        self.assertEqual(june_events[0]["display"], "block")
        self.assertEqual(june_events[0]["extendedProps"]["endDate"], "2027-07-02")
        self.assertTrue(june_events[0]["extendedProps"]["multiDay"])
        self.assertEqual(july_events[0]["start"], "2027-06-28")
        self.assertEqual(july_events[0]["end"], "2027-07-03")

    def test_single_day_event_stays_a_dot(self):
        response = self.client.post(
            "/events/add",
            data={
                "title": "Branch council",
                "event_date": "2027-06-14",
                "start_time": "19:00",
                "end_time": "20:00",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = self.client.get("/api/events?start=2027-06-01T00:00:00&end=2027-07-01T00:00:00").get_json()
        council = next(item for item in payload if item["extendedProps"]["fullTitle"] == "Branch council")
        self.assertNotIn("display", council)
        self.assertIn("cal-compact-event", council["classNames"])
        self.assertFalse(council["extendedProps"]["multiDay"])
        self.assertTrue(council["start"].startswith("2027-06-14T19:00"))
        self.assertTrue(council["end"].startswith("2027-06-14T20:00"))

    def test_add_event_rejects_end_before_start(self):
        response = self.client.post(
            "/events/add",
            data={
                "title": "Backwards",
                "event_date": "2027-06-18",
                "event_end_date": "2027-06-10",
                "all_day": "1",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("on or after", response.get_json()["error"])
        with self.app.app_context():
            self.assertEqual(Event.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
