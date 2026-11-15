"""Upcoming and past interview lists, split on the Central-time clock."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.interview_schedule import app_now, partition_interviews


def _interview(**kwargs):
    defaults = dict(
        id=1,
        starts_at=datetime(2026, 11, 15, 9, 0),
        duration_minutes=15,
        purpose="Interview",
        recurrence_freq=None,
        recurrence_interval=1,
        recurrence_byweekday=None,
        recurrence_until=None,
        recurrence_bysetpos=None,
        who_text="",
        member_id=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class PartitionTests(unittest.TestCase):
    def test_later_today_is_upcoming_and_earlier_today_is_past(self):
        # 4:00 PM Central. 7:00 PM the same day has not happened yet.
        # 7:00 PM Central is already the next UTC date, so a UTC clock would
        # file it under past if the stored wall time were compared to UTC.
        now = datetime(2026, 11, 15, 16, 0)
        morning = _interview(id=1, starts_at=datetime(2026, 11, 15, 9, 0), who_text="Earlier today")
        evening = _interview(id=2, starts_at=datetime(2026, 11, 15, 19, 0), who_text="Later today")
        upcoming, past = partition_interviews([morning, evening], now)
        self.assertEqual([entry.interview.who_text for entry in upcoming], ["Later today"])
        self.assertEqual([entry.when for entry in upcoming], [datetime(2026, 11, 15, 19, 0)])
        self.assertEqual([entry.interview.who_text for entry in past], ["Earlier today"])

    def test_a_start_at_this_minute_stays_upcoming(self):
        now = datetime(2026, 11, 15, 16, 0)
        upcoming, past = partition_interviews([_interview(starts_at=now)], now)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(past, [])

    def test_upcoming_is_soonest_first_and_past_is_most_recent_first(self):
        now = datetime(2026, 11, 15, 12, 0)
        rows = [
            _interview(id=1, starts_at=datetime(2026, 12, 1, 9, 0), who_text="December"),
            _interview(id=2, starts_at=datetime(2026, 11, 16, 9, 0), who_text="Tomorrow"),
            _interview(id=3, starts_at=datetime(2026, 11, 20, 9, 0), who_text="Next week"),
            _interview(id=4, starts_at=datetime(2026, 11, 1, 9, 0), who_text="Nov 1"),
            _interview(id=5, starts_at=datetime(2026, 11, 14, 9, 0), who_text="Yesterday"),
            _interview(id=6, starts_at=datetime(2026, 10, 1, 9, 0), who_text="October"),
        ]
        upcoming, past = partition_interviews(rows, now)
        self.assertEqual(
            [entry.interview.who_text for entry in upcoming],
            ["Tomorrow", "Next week", "December"],
        )
        self.assertEqual(
            [entry.interview.who_text for entry in past],
            ["Yesterday", "Nov 1", "October"],
        )

    def test_open_series_lists_the_next_visit_not_the_day_it_started(self):
        # Weekly Tuesday 7:00 PM that began in October. On Sunday Nov 15 the
        # next visit is Tuesday Nov 17, so the series is upcoming.
        now = datetime(2026, 11, 15, 16, 0)
        series = _interview(
            id=7,
            starts_at=datetime(2026, 10, 6, 19, 0),
            recurrence_freq="weekly",
            recurrence_byweekday="TU",
            recurrence_until=date(2026, 12, 31),
            who_text="Counseling",
        )
        upcoming, past = partition_interviews([series], now)
        self.assertEqual(past, [])
        self.assertEqual(upcoming[0].when, datetime(2026, 11, 17, 19, 0))

    def test_series_meeting_later_today_is_upcoming(self):
        now = datetime(2026, 11, 15, 16, 0)
        series = _interview(
            id=8,
            starts_at=datetime(2026, 10, 4, 18, 0),
            recurrence_freq="weekly",
            recurrence_byweekday="SU",
            recurrence_until=date(2026, 12, 31),
        )
        upcoming, past = partition_interviews([series], now)
        self.assertEqual(past, [])
        self.assertEqual(upcoming[0].when, datetime(2026, 11, 15, 18, 0))

    def test_ended_series_is_past_and_sorts_by_its_last_day(self):
        now = datetime(2026, 11, 15, 16, 0)
        ended = _interview(
            id=9,
            starts_at=datetime(2026, 1, 6, 19, 0),
            recurrence_freq="weekly",
            recurrence_byweekday="TU",
            recurrence_until=date(2026, 10, 27),
            who_text="Ended",
        )
        older = _interview(id=10, starts_at=datetime(2026, 8, 1, 10, 0), who_text="August")
        upcoming, past = partition_interviews([older, ended], now)
        self.assertEqual(upcoming, [])
        self.assertEqual([entry.interview.who_text for entry in past], ["Ended", "August"])
        self.assertEqual(past[0].when, datetime(2026, 10, 27, 19, 0))

    def test_one_off_and_series_share_one_soonest_first_list(self):
        now = datetime(2026, 11, 15, 16, 0)
        later_today = _interview(id=1, starts_at=datetime(2026, 11, 15, 19, 0), who_text="Tonight")
        next_month = _interview(id=2, starts_at=datetime(2026, 12, 20, 11, 0), who_text="December")
        series = _interview(
            id=3,
            starts_at=datetime(2026, 10, 6, 19, 0),
            recurrence_freq="weekly",
            recurrence_byweekday="TU",
            recurrence_until=date(2026, 12, 29),
            who_text="Tuesday series",
        )
        upcoming, _past = partition_interviews([next_month, series, later_today], now)
        self.assertEqual(
            [entry.interview.who_text for entry in upcoming],
            ["Tonight", "Tuesday series", "December"],
        )
        self.assertEqual(
            [entry.when for entry in upcoming],
            [
                datetime(2026, 11, 15, 19, 0),
                datetime(2026, 11, 17, 19, 0),
                datetime(2026, 12, 20, 11, 0),
            ],
        )

    def test_app_now_is_chicago_wall_time(self):
        got = app_now()
        expected = datetime.now(ZoneInfo("America/Chicago")).replace(tzinfo=None)
        self.assertIsNone(got.tzinfo)
        self.assertLess(abs(got - expected), timedelta(seconds=2))


class InterviewsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_file.close()
        cls._prev_db = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["INIT_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["INIT_ADMIN_PASSWORD"] = "test-password-123"
        from app import create_app, db

        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.db = db
        cls.client = cls.app.test_client()
        if cls._prev_db is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls._prev_db

    def setUp(self):
        from app.models import Interview, Member

        with self.app.app_context():
            Interview.query.delete()
            Member.query.delete()
            self.db.session.commit()
        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "test-password-123"},
            follow_redirects=True,
        )

    def _seed(self):
        from app.models import Interview, Member

        with self.app.app_context():
            members = {}
            for name in (
                "Noah Ellis",
                "Maya Chen",
                "Owen Price",
                "Priya Shah",
                "Luis Ortega",
                "Hannah Kim",
                "Grace Patel",
                "Caleb Nguyen",
                "July Brooks",
                "June Harper",
                "Ruth Alvarez",
            ):
                member = Member(full_name=name)
                self.db.session.add(member)
                members[name] = member
            self.db.session.commit()

            def add(who, starts, purpose, **extra):
                self.db.session.add(
                    Interview(
                        member_id=members[who].id if who else None,
                        starts_at=starts,
                        duration_minutes=extra.pop("duration_minutes", 15),
                        purpose=purpose,
                        **extra,
                    )
                )

            add("Noah Ellis", datetime(2026, 12, 20, 11, 0), "Temple recommend")
            add("Maya Chen", datetime(2026, 11, 22, 14, 0), "Mission prep")
            add(None, datetime(2026, 11, 15, 19, 0), "Bishop interview", who_text="Stake presidency", duration_minutes=30)
            add("Owen Price", datetime(2026, 11, 15, 9, 0), "Temple recommend")
            add("Priya Shah", datetime(2026, 11, 10, 18, 30), "New member")
            add("Luis Ortega", datetime(2026, 11, 1, 10, 0), "Calling")
            add("Hannah Kim", datetime(2026, 10, 15, 16, 0), "Youth interview")
            add("Grace Patel", datetime(2026, 9, 8, 19, 0), "Temple recommend")
            add("Caleb Nguyen", datetime(2026, 8, 4, 18, 0), "Counseling")
            add("July Brooks", datetime(2026, 7, 7, 17, 0), "Temple recommend")
            add("June Harper", datetime(2026, 6, 2, 18, 30), "Mission prep")
            add(
                "Ruth Alvarez",
                datetime(2026, 10, 6, 19, 0),
                "Regular counseling",
                duration_minutes=20,
                recurrence_freq="weekly",
                recurrence_interval=1,
                recurrence_byweekday="TU",
                recurrence_until=date(2026, 12, 29),
            )
            self.db.session.commit()

    def test_page_splits_upcoming_and_past_around_central_time(self):
        self._seed()
        with patch("app.interview_schedule.app_now", return_value=datetime(2026, 11, 15, 16, 0)):
            response = self.client.get("/interviews")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("Recent interviews", html)
        self.assertIn('rel="manifest"', html)
        self.assertIn("Central time", html)

        upcoming = _section(html, "upcoming-interviews", "repeating-interviews")
        past = html[html.find('id="past-interviews"') :]
        self.assertLess(html.find('id="upcoming-interviews"'), html.find('id="repeating-interviews"'))
        self.assertLess(html.find('id="repeating-interviews"'), html.find('id="past-interviews"'))

        for earlier, later in (
            ("Stake presidency", "Ruth Alvarez"),
            ("Ruth Alvarez", "Maya Chen"),
            ("Maya Chen", "Noah Ellis"),
        ):
            self.assertLess(upcoming.find(earlier), upcoming.find(later))
        self.assertIn("Sun Nov 15, 2026 07:00 PM", upcoming)
        self.assertIn("Bishop interview", upcoming)
        self.assertIn("Tue Nov 17, 2026 07:00 PM", upcoming)
        self.assertNotIn("Oct 06, 2026", upcoming)

        details_at = past.find("<details")
        self.assertGreater(details_at, 0)
        visible = past[:details_at]
        hidden = past[details_at:]
        for earlier, later in (
            ("Owen Price", "Priya Shah"),
            ("Priya Shah", "Luis Ortega"),
            ("Luis Ortega", "Hannah Kim"),
            ("Hannah Kim", "Grace Patel"),
            ("Grace Patel", "Caleb Nguyen"),
        ):
            self.assertLess(visible.find(earlier), visible.find(later))
        self.assertNotIn("June Harper", visible)
        self.assertNotIn("July Brooks", visible)
        self.assertIn("Show 2 earlier interviews", hidden)
        self.assertLess(hidden.find("July Brooks"), hidden.find("June Harper"))
        self.assertIn("Sun Nov 15, 2026 09:00 AM", visible)

    def test_empty_lists_say_so(self):
        with patch("app.interview_schedule.app_now", return_value=datetime(2026, 11, 15, 16, 0)):
            response = self.client.get("/interviews")
        html = response.get_data(as_text=True)
        self.assertIn("No upcoming interviews.", html)
        self.assertIn("No past interviews.", html)
        self.assertNotIn("interview-table", html)


def _section(html: str, start_id: str, end_id: str) -> str:
    start = html.find(f'id="{start_id}"')
    end = html.find(f'id="{end_id}"')
    if start < 0 or end < start:
        raise AssertionError(f"missing section {start_id}..{end_id}")
    return html[start:end]
