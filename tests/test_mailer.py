import unittest
from unittest.mock import patch

from mailer import notify_session_request


class MailerTests(unittest.TestCase):
    request = {
        "id": "request-1",
        "student_first_name": "Maya",
        "guardian_name": "Rana",
        "guardian_email": "guardian@example.com",
        "subject": "Math",
        "student_grade": 6,
        "notes": "Fractions",
        "status": "requested",
        "tutors": {"full_name": "Layla A.", "tutor_email": "tutor@example.com"},
        "availability_slots": {
            "starts_at": "2026-12-01T12:00:00+00:00",
            "ends_at": "2026-12-01T13:00:00+00:00",
            "timezone": "Asia/Damascus",
        },
    }

    def test_request_sends_separate_role_specific_emails(self):
        with patch("mailer.send_email", return_value=True) as send:
            self.assertTrue(notify_session_request(self.request))
        self.assertEqual(send.call_count, 2)
        calls = {item.kwargs["to"]: item.kwargs for item in send.call_args_list}
        self.assertEqual(set(calls), {"guardian@example.com", "tutor@example.com"})
        self.assertIn("received your lesson request", calls["guardian@example.com"]["html"])
        self.assertIn("new lesson request", calls["tutor@example.com"]["html"])
        self.assertIn("waiting for approval", calls["tutor@example.com"]["html"])
        self.assertEqual(calls["guardian@example.com"]["subject"], "TM Tutoring request received")

    def test_any_email_failure_returns_false_without_resaving(self):
        with patch("mailer.send_email", side_effect=(True, False)) as send:
            self.assertFalse(notify_session_request(self.request))
        self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
