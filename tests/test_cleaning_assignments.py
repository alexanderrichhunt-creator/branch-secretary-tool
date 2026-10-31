"""Weekly church-cleaning assignments, calendar display, and the printable month."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date

from werkzeug.datastructures import MultiDict

from app.cleaning import format_week_long, format_week_range, parse_week_start, week_start_sunday


class WeekParsingTests(unittest.TestCase):
    def test_any_day_snaps_to_sunday(self):
        # Wednesday, October 28, 2026 belongs to the week of Sunday the 25th.
        self.assertEqual(parse_week_start("2026-10-28"), date(2026, 10, 25))
        self.assertEqual(week_start_sunday(date(2026, 10, 25)), date(2026, 10, 25))

    def test_iso_week_uses_the_sunday_inside_it(self):
        # ISO week 2026-W43 is Mon Oct 19 – Sun Oct 25. Church week starts that Sunday.
        sunday = date(2026, 10, 25)
        iso = sunday.isocalendar()
        raw = f"{iso.year}-W{iso.week:02d}"
        self.assertEqual(parse_week_start(raw), sunday)

    def test_blank_and_garbage_are_rejected(self):
        self.assertIsNone(parse_week_start(""))
        self.assertIsNone(parse_week_start("not-a-week"))
        self.assertIsNone(parse_week_start("2026-W99"))

    def test_range_labels(self):
        self.assertEqual(format_week_range(date(2026, 10, 25)), "Oct 25 – 31, 2026")
        self.assertIn("Sunday, October 25", format_week_long(date(2026, 10, 25)))
        self.assertIn("Saturday, October 31, 2026", format_week_long(date(2026, 10, 25)))


class CleaningAssignmentTests(unittest.TestCase):
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
        from app.models import CleaningAssignment, Event, Member

        with self.app.app_context():
            for row in CleaningAssignment.query.all():
                row.members = []
            CleaningAssignment.query.delete()
            Event.query.delete()
            Member.query.delete()
            self.db.session.commit()
            self.members = []
            for name in ("Anna Brooks", "Ben Carter", "Clara Diaz"):
                member = Member(full_name=name)
                self.db.session.add(member)
                self.members.append(member)
            self.db.session.commit()
            self.member_ids = [member.id for member in self.members]
        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "test-password-123"},
            follow_redirects=True,
        )

    def _save(self, week: str, member_ids: list[int]):
        data = MultiDict([("week_start", week)])
        for member_id in member_ids:
            data.add("member_ids", str(member_id))
        return self.client.post("/cleaning", data=data, follow_redirects=True)

    def test_save_replaces_the_same_week_and_keeps_other_weeks(self):
        from app.models import CleaningAssignment

        first = self._save("2026-10-28", self.member_ids[:2])
        self.assertEqual(first.status_code, 200)
        self.assertIn(b"Anna Brooks", first.data)
        self.assertIn(b"Ben Carter", first.data)

        second = self._save("2026-10-25", [self.member_ids[2]])
        self.assertIn(b"Updated cleaning", second.data)
        self.assertIn(b"Clara Diaz", second.data)

        other = self._save("2026-11-02", [self.member_ids[0]])
        self.assertIn(b"Saved cleaning", other.data)

        with self.app.app_context():
            rows = CleaningAssignment.query.order_by(CleaningAssignment.week_start).all()
            self.assertEqual([row.week_start for row in rows], [date(2026, 10, 25), date(2026, 11, 1)])
            self.assertEqual(rows[0].cleaner_names(), ["Clara Diaz"])
            self.assertEqual(rows[1].cleaner_names(), ["Anna Brooks"])

    def test_empty_selection_is_rejected(self):
        from app.models import CleaningAssignment

        response = self.client.post("/cleaning", data={"week_start": "2026-10-25"}, follow_redirects=True)
        self.assertIn(b"at least one person", response.data)
        with self.app.app_context():
            self.assertEqual(CleaningAssignment.query.count(), 0)

    def test_cleaning_stays_off_the_main_calendar(self):
        self._save("2026-10-25", self.member_ids[:2])
        self.client.post(
            "/events/add",
            data={
                "title": "Youth activity",
                "event_date": "2026-10-28",
                "start_time": "19:00",
                "end_time": "20:30",
                "category": "youth",
                "respond_json": "1",
            },
        )
        main = self.client.get(
            "/api/events?start=2026-10-01T00:00:00&end=2026-11-01T00:00:00"
        ).get_json()
        self.assertFalse(any(item["extendedProps"].get("kind") == "cleaning" for item in main))
        youth = next(item for item in main if item["extendedProps"].get("fullTitle") == "Youth activity")
        self.assertEqual(youth["extendedProps"]["kind"], "event")
        self.assertEqual(youth["extendedProps"]["category"], "youth")

        cleaning = self.client.get(
            "/api/cleaning?start=2026-10-01T00:00:00&end=2026-11-01T00:00:00"
        ).get_json()
        self.assertEqual(len(cleaning), 1)
        self.assertEqual(cleaning[0]["extendedProps"]["kind"], "cleaning")
        self.assertIn("Anna Brooks", cleaning[0]["extendedProps"]["cleaners"])
        self.assertNotIn("Youth activity", cleaning[0]["title"])

        page = self.client.get("/cleaning?week=2026-10-25")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"cleaning-calendar", page.data)
        self.assertIn(b"/api/cleaning", page.data)

    def test_prints_are_separate_and_main_print_respects_filters(self):
        self._save("2026-10-25", self.member_ids[:2])
        self._save("2026-11-01", [self.member_ids[2]])
        self.client.post(
            "/events/add",
            data={
                "title": "Youth activity",
                "event_date": "2026-10-28",
                "start_time": "19:00",
                "end_time": "20:30",
                "category": "youth",
                "respond_json": "1",
            },
        )
        self.client.post(
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

        main_print = self.client.get("/calendar/print?month=2026-10").get_data(as_text=True)
        self.assertIn("October 2026", main_print)
        self.assertIn("Youth activity", main_print)
        self.assertIn("All event types", main_print)
        self.assertNotIn("Anna Brooks", main_print)
        self.assertNotIn("Church cleaning calendar", main_print)

        hidden = self.client.get("/calendar/print?month=2026-10&hide=youth").get_data(as_text=True)
        self.assertNotIn("Youth activity", hidden)
        self.assertIn("Hidden: Youth Events", hidden)

        june = self.client.get("/calendar/print?month=2027-06").get_data(as_text=True)
        self.assertIn("Nauvoo Trip", june)
        no_span = self.client.get("/calendar/print?month=2027-06&hide=multiday").get_data(as_text=True)
        self.assertNotIn("Nauvoo Trip", no_span)
        self.assertIn("Hidden: Multi-day", no_span)

        cleaning_print = self.client.get("/cleaning/print?month=2026-10").get_data(as_text=True)
        self.assertIn("Church cleaning calendar", cleaning_print)
        self.assertIn("print-week-grid", cleaning_print)
        self.assertIn("print-week-names", cleaning_print)
        self.assertIn('<span class="print-cleaning-name">Anna Brooks</span>', cleaning_print)
        self.assertIn('<span class="print-cleaning-name">Ben Carter</span>', cleaning_print)
        self.assertNotIn("Anna Brooks, Ben Carter", cleaning_print)
        self.assertNotIn("print-week-box", cleaning_print)
        self.assertNotIn("print-week-assignment", cleaning_print)
        self.assertNotIn("print-cleaning-row", cleaning_print)
        self.assertNotIn("Youth activity", cleaning_print)
        self.assertNotIn("Clara Diaz", cleaning_print)
        # Each name is its own line, inside that week's squares, after the day numbers.
        anna_at = cleaning_print.find("Anna Brooks")
        ben_at = cleaning_print.find("Ben Carter")
        week_at = cleaning_print.rfind("print-week-grid", 0, anna_at)
        self.assertGreater(week_at, -1)
        self.assertGreater(ben_at, anna_at)
        self.assertIn(">25<", cleaning_print[week_at:anna_at])
        self.assertIn(">31<", cleaning_print[week_at:anna_at])

        november = self.client.get("/cleaning/print?month=2026-11").get_data(as_text=True)
        self.assertIn("Clara Diaz", november)

    def test_delete_removes_the_week(self):
        from app.models import CleaningAssignment

        self._save("2026-10-25", [self.member_ids[0]])
        with self.app.app_context():
            assignment_id = CleaningAssignment.query.one().id
        response = self.client.post(
            f"/cleaning/{assignment_id}/delete",
            headers={"X-Requested-With": "fetch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        with self.app.app_context():
            self.assertEqual(CleaningAssignment.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
