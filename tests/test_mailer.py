import unittest
from unittest.mock import patch

from mailer import notify_session_request, notify_session_status, send_email


class MailerTests(unittest.TestCase):
    request = {
        "id": "request-1",
        "student_first_name": "Maya",
        "guardian_name": "Rana",
        "guardian_email": "guardian@example.com",
        "subject": "Math",
        "student_grade": 6,
        "notes": "Fractions",
        "status": "confirmed",
        "student_timezone": "Asia/Dubai",
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
        self.assertIn("lesson is confirmed", calls["guardian@example.com"]["html"])
        self.assertIn("lesson has been booked", calls["tutor@example.com"]["html"])
        self.assertIn("confirmed automatically", calls["tutor@example.com"]["html"])
        self.assertEqual(calls["guardian@example.com"]["subject"], "ClassMatch lesson confirmed")

    def test_any_email_failure_returns_false_without_resaving(self):
        with patch("mailer.send_email", side_effect=(True, False)) as send:
            self.assertFalse(notify_session_request(self.request))
        self.assertEqual(send.call_count, 2)

    def test_retry_targets_only_failed_recipient(self):
        with patch("mailer.send_email", return_value=True) as send:
            self.assertTrue(notify_session_request(self.request, recipients={"tutor@example.com"}))
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.kwargs["to"], "tutor@example.com")

    def test_status_email_uses_each_recipient_timezone(self):
        confirmed = {**self.request, "status": "confirmed", "meeting_url": "https://meet.example/lesson"}
        with patch("mailer.send_email", return_value=True) as send:
            self.assertTrue(notify_session_status(confirmed))
        calls = {item.kwargs["to"]: item.kwargs for item in send.call_args_list}
        self.assertEqual(set(calls), {"guardian@example.com", "tutor@example.com"})
        self.assertIn("16:00", calls["guardian@example.com"]["html"])
        self.assertIn("15:00", calls["tutor@example.com"]["html"])

    def test_decline_immediately_emails_both_people(self):
        declined = {**self.request, "status": "declined", "meeting_url": None}
        with patch("mailer.send_email", return_value=True) as send:
            self.assertTrue(notify_session_status(declined))
        self.assertEqual(send.call_count, 2)
        calls = {item.kwargs["to"]: item.kwargs for item in send.call_args_list}
        self.assertEqual(set(calls), {"guardian@example.com", "tutor@example.com"})
        self.assertTrue(all("session declined" in item["subject"].lower() for item in calls.values()))
        self.assertTrue(all("can no longer go ahead" in item["html"] for item in calls.values()))

    def test_successful_email_is_not_sent_again_after_a_rerun(self):
        with patch("mailer.email_was_sent", return_value=True), patch("mailer.resend.Emails.send") as send:
            self.assertTrue(send_email(event_type="session_confirmed_reserver", to="guardian@example.com", subject="Confirmed", html="ok", related_id="request-1"))
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
