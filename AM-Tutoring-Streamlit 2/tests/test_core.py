from datetime import date, time
import unittest

from core import build_recurring_slots, format_slot, public_name, valid_meeting_url


class CoreTests(unittest.TestCase):
    def test_public_name_hides_full_surname(self):
        self.assertEqual(public_name("Layla Al Ali"), "Layla A.")
        self.assertEqual(public_name("Omar"), "Omar")

    def test_recurring_slot_count_and_breaks(self):
        rows = build_recurring_slots("tutor", date(2026, 9, 14), [0, 2], 2, time(16), time(18), 45, 15, "Asia/Dubai")
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["status"], "open")
        self.assertLess(rows[0]["starts_at"], rows[0]["ends_at"])

    def test_recurring_slot_validation(self):
        with self.assertRaisesRegex(ValueError, "weekday"):
            build_recurring_slots("tutor", date.today(), [], 1, time(16), time(18), 60, 0, "Asia/Dubai")
        with self.assertRaisesRegex(ValueError, "after"):
            build_recurring_slots("tutor", date.today(), [0], 1, time(18), time(16), 60, 0, "Asia/Dubai")

    def test_secure_meeting_link(self):
        self.assertEqual(valid_meeting_url("https://meet.google.com/abc"), "https://meet.google.com/abc")
        for value in ("http://example.com", "javascript:alert(1)", "https://user:pass@example.com"):
            with self.assertRaises(ValueError):
                valid_meeting_url(value)

    def test_slot_formatting(self):
        label = format_slot({"starts_at": "2026-09-15T12:00:00+00:00", "ends_at": "2026-09-15T13:00:00+00:00", "timezone": "Asia/Dubai"})
        self.assertIn("16:00–17:00", label)
        self.assertIn("Dubai", label)


if __name__ == "__main__":
    unittest.main()
