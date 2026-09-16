import unittest
from unittest.mock import patch

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Streamlit testing support is unavailable")
class SmokeTests(unittest.TestCase):
    tutor = {
        "id": "tutor-1", "full_name": "Layla A.", "age": 16, "school_grade": 11,
        "country": "Syria", "subjects": ["Math"], "languages": ["Arabic", "English"],
        "min_student_grade": 1, "max_student_grade": 8, "bio": "A patient math tutor.",
    }
    slot = {
        "id": "slot-1", "tutor_id": "tutor-1", "starts_at": "2026-12-01T12:00:00+00:00",
        "ends_at": "2026-12-01T13:00:00+00:00", "timezone": "Asia/Damascus", "status": "open",
    }

    @staticmethod
    def button(app, label):
        return next(item for item in app.button if item.label == label)

    def open_tutor_results(self, *, signed_in=False):
        user = {"id": "user-1", "email": "guardian@example.com"} if signed_in else None
        stack = [
            patch("auth.current_user", return_value=user),
            patch("backend.configuration_missing", return_value=[]),
            patch("backend.public_tutors", return_value=[self.tutor]),
            patch("backend.open_slot_summaries", return_value={"tutor-1": {"count": 1, "next_slot": self.slot}}),
            patch("backend.open_slots", return_value=[self.slot]),
        ]
        for item in stack:
            item.start()
            self.addCleanup(item.stop)
        app = AppTest.from_file("app.py").run(timeout=20)
        app.radio[0].set_value("Find a tutor").run(timeout=20)
        next(item for item in app.selectbox if item.label == "Grade").set_value(1)
        next(item for item in app.selectbox if item.label == "Subject").set_value("Math")
        self.button(app, "Find matching tutors  →").click().run(timeout=20)
        return app

    def test_home_renders_without_credentials(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Students learning" in item.value and "tutors who <em>care" in item.value for item in app.markdown))
        self.assertTrue(any("TM Tutoring" in item.value and "mail.google.com/mail/" in item.value for item in app.markdown))
        self.assertTrue(any('class="privacy-home-link"' in item.value and '?view=privacy' in item.value for item in app.markdown))
        self.assertFalse(any(item.label == "Privacy & safeguarding" for item in app.button))
        self.assertFalse(any("mailto:" in item.value or "AM Tutoring" in item.value for item in app.markdown))
        self.assertTrue(any("Setup is not finished" in warning.value for warning in app.warning))

    def test_privacy_link_opens_a_dedicated_page(self):
        app = AppTest.from_file("app.py")
        app.query_params["view"] = "privacy"
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Clear rules for safer learning" in item.value for item in app.markdown))
        self.assertTrue(any("Email privacy support" in item.value for item in app.markdown))
        self.assertEqual(app.radio[0].options, ["Home", "Find a tutor", "My account"])
        app.radio[0].set_value("Home").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Students learning" in item.value for item in app.markdown))

    def test_public_navigation_and_missing_backend_error(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("inner-page-title\">Find a tutor" in item.value for item in app.markdown))
        next(item for item in app.selectbox if item.label == "Grade").set_value(1)
        next(item for item in app.selectbox if item.label == "Subject").set_value("Math")
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("database connection" in error.value.lower() for error in app.error))

    def test_account_page_renders(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        app.radio[0].set_value("My account").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("inner-page-title\">My account" in item.value for item in app.markdown))
        self.assertEqual([tab.label for tab in app.tabs], ["Sign in", "Create account", "Reset password"])

    def test_account_history_handles_missing_related_tutor(self):
        user = {"id": "user-1", "email": "guardian@example.com"}
        history = [{"id": "request-1", "student_first_name": "Maya", "subject": "Math", "status": "requested", "meeting_url": None, "tutors": None, "availability_slots": None}]
        with patch("auth.current_user", return_value=user), patch("auth.is_owner", return_value=False), patch("auth.access_token", return_value="access-token"), patch("backend.configuration_missing", return_value=[]), patch("backend.user_session_requests", return_value=history):
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("My account").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Tutor unavailable" in item.value for item in app.subheader))

    def test_sign_in_returns_to_saved_booking_page(self):
        with patch("auth.current_user", return_value=None), patch("auth.sign_in") as sign_in_mock, patch("backend.configuration_missing", return_value=[]):
            app = AppTest.from_file("app.py")
            app.session_state["page"] = "My account"
            app.session_state["return_page_after_auth"] = "Find a tutor"
            app.run(timeout=20)
            next(item for item in app.text_input if item.label == "Email").set_value("guardian@example.com")
            next(item for item in app.text_input if item.label == "Password").set_value("safe-password")
            self.button(app, "Sign in").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(sign_in_mock.call_count, 1)
        self.assertEqual(app.session_state.filtered_state["page"], "Find a tutor")

    def test_matching_tutor_is_a_private_profile_card(self):
        app = self.open_tutor_results()
        self.assertFalse(app.exception)
        self.assertTrue(any("Layla A." in item.value and "tutor-profile-flat" in item.value for item in app.markdown))
        profiles = [item.value for item in app.markdown if '<article class="tutor-profile' in item.value]
        self.assertTrue(profiles)
        self.assertFalse(any("@" in value for value in profiles))
        self.assertFalse(any(item.label == "Country" for item in app.selectbox))

    def test_tutor_dashboard_is_hidden_from_unassigned_students(self):
        user = {"id": "user-1", "email": "student@example.com"}
        with patch("auth.current_user", return_value=user), patch("backend.configuration_missing", return_value=[]), patch("backend.tutor_assignment", return_value=None):
            app = AppTest.from_file("app.py")
            app.session_state["page"] = "Tutor dashboard"
            app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("has not been assigned" in item.value for item in app.error))

    def test_assigned_tutor_sees_only_tutor_dashboard_data(self):
        user = {"id": "user-1", "email": "tutor@example.com"}
        assignment = {"id": "role-1", "email": user["email"], "tutor_id": "tutor-1", "timezone": "Asia/Dubai", "timezone_confirmed": True, "tutors": {"id": "tutor-1", "full_name": "Layla A.", "country": "UAE", "active": True}}
        lesson = {"id": "request-1", "tutor_id": "tutor-1", "student_first_name": "Maya", "student_grade": 6, "subject": "Math", "guardian_email": "family@example.com", "notes": "Fractions", "status": "confirmed", "meeting_url": None, "availability_slots": self.slot}
        with patch("auth.current_user", return_value=user), patch("auth.access_token", return_value="access-token"), patch("backend.configuration_missing", return_value=[]), patch("backend.tutor_assignment", return_value=assignment), patch("backend.tutor_slots", return_value=[self.slot]), patch("backend.tutor_session_requests", return_value=[lesson]):
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("Tutor dashboard").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Tutor dashboard" in item.value for item in app.markdown))
        self.assertTrue(any("family@example.com" in item.value and "Fractions" in item.value for item in app.markdown))

    def test_unauthenticated_selection_requires_sign_in(self):
        app = self.open_tutor_results()
        self.button(app, "Choose this tutor  →").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Sign in before choosing a time" in item.value for item in app.warning))

    def test_details_lead_to_review_without_saving(self):
        app = self.open_tutor_results(signed_in=True)
        self.button(app, "Choose this tutor  →").click().run(timeout=20)
        next(item for item in app.selectbox if item.label == "Your timezone").set_value("Asia/Dubai").run(timeout=20)
        self.button(app, "Continue to student details  →").click().run(timeout=20)
        next(item for item in app.text_input if item.label == "Student’s first name only").set_value("Maya")
        next(item for item in app.text_input if item.label == "Parent, guardian, or reserver name").set_value("Rana")
        app.checkbox[0].set_value(True)
        self.button(app, "Review reservation  →").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("review-card" in item.value and "Maya" in item.value and "Rana" in item.value for item in app.markdown))

    def test_confirm_saves_once_then_shows_confirmation(self):
        booking = {
            "id": "request-1", "availability_slots": self.slot,
            "tutors": {"full_name": "Layla A.", "tutor_email": "tutor@example.com"},
            "guardian_email": "guardian@example.com",
        }
        request_patcher = patch("backend.request_session", return_value=booking)
        email_patcher = patch("mailer.notify_session_request", return_value=True)
        token_patcher = patch("auth.access_token", return_value="access-token")
        request_mock, email_mock = request_patcher.start(), email_patcher.start()
        token_patcher.start()
        self.addCleanup(request_patcher.stop)
        self.addCleanup(email_patcher.stop)
        self.addCleanup(token_patcher.stop)
        app = self.open_tutor_results(signed_in=True)
        self.button(app, "Choose this tutor  →").click().run(timeout=20)
        next(item for item in app.selectbox if item.label == "Your timezone").set_value("Asia/Dubai").run(timeout=20)
        self.button(app, "Continue to student details  →").click().run(timeout=20)
        next(item for item in app.text_input if item.label == "Student’s first name only").set_value("Maya")
        next(item for item in app.text_input if item.label == "Parent, guardian, or reserver name").set_value("Rana")
        app.checkbox[0].set_value(True)
        self.button(app, "Review reservation  →").click().run(timeout=20)
        self.button(app, "Confirm reservation  →").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(request_mock.call_count, 1)
        self.assertEqual(email_mock.call_count, 1)
        self.assertTrue(any("Your reservation is in" in item.value for item in app.markdown))

    def test_student_can_cancel_own_upcoming_reservation(self):
        user = {"id": "user-1", "email": "guardian@example.com"}
        history = [{"id": "request-1", "student_first_name": "Maya", "guardian_name": "Rana", "guardian_email": user["email"], "student_grade": 6, "subject": "Math", "status": "confirmed", "meeting_url": None, "student_timezone": "Asia/Dubai", "tutors": {"full_name": "Layla A.", "tutor_email": "tutor@example.com"}, "availability_slots": self.slot}]
        cancelled = {**history[0], "status": "cancelled"}
        with patch("auth.current_user", return_value=user), patch("auth.is_owner", return_value=False), patch("auth.access_token", return_value="access-token"), patch("backend.configuration_missing", return_value=[]), patch("backend.user_session_requests", return_value=history), patch("backend.cancel_user_session", return_value=cancelled) as cancel, patch("mailer.notify_session_status", return_value=True):
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("My account").run(timeout=20)
            next(item for item in app.checkbox if item.label.startswith("I understand")).set_value(True)
            self.button(app, "Cancel reservation").click().run(timeout=20)
        self.assertFalse(app.exception)
        cancel.assert_called_once_with("request-1", "access-token")

    def test_signed_out_owner_page_does_not_claim_session_expired(self):
        with patch("auth.current_user", return_value=None), patch("backend.configuration_missing", return_value=[]):
            app = AppTest.from_file("app.py")
            app.session_state["page"] = "Owner dashboard"
            app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Sign in with an approved owner account" in item.value for item in app.error))
        self.assertFalse(any("expired" in item.value.lower() for item in app.error))

    def test_invalid_tutor_form_stays_on_owner_dashboard(self):
        owner = {"id": "owner-1", "email": "taleenalali5@gmail.com"}
        with patch("auth.current_user", return_value=owner), patch("auth.is_owner", return_value=True), patch("backend.configuration_missing", return_value=[]), patch("backend.managed_tutors", return_value=[]), patch("backend.add_tutor") as add_mock:
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("Owner dashboard").run(timeout=20)
            self.button(app, "Publish tutor  →").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(add_mock.call_count, 0)
        self.assertEqual(app.session_state.filtered_state["page"], "Owner dashboard")
        self.assertTrue(any("public tutor name" in item.value for item in app.error))

    def test_valid_tutor_publishes_once_and_keeps_owner_section(self):
        owner = {"id": "owner-1", "email": "taleenalali5@gmail.com"}
        saved = {"id": "tutor-1", "full_name": "Layla A."}
        with patch("auth.current_user", return_value=owner), patch("auth.is_owner", return_value=True), patch("backend.configuration_missing", return_value=[]), patch("backend.managed_tutors", return_value=[]), patch("backend.add_tutor", return_value=saved) as add_mock:
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("Owner dashboard").run(timeout=20)
            next(item for item in app.text_input if item.label == "Public tutor name").set_value("Layla A.")
            next(item for item in app.text_input if item.label == "Private tutor email").set_value("layla@example.com")
            next(item for item in app.number_input if item.label == "Age").set_value(35)
            next(item for item in app.selectbox if item.label == "Country").set_value("France")
            next(item for item in app.multiselect if item.label == "Subjects taught").set_value(["Math"])
            next(item for item in app.multiselect if item.label == "Languages").set_value(["Arabic"])
            app.text_area[0].set_value("Patient and friendly.")
            self.button(app, "Publish tutor  →").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(add_mock.call_count, 1)
        self.assertEqual(add_mock.call_args.args[0]["age"], 35)
        self.assertEqual(add_mock.call_args.args[0]["country"], "France")
        self.assertEqual(app.session_state.filtered_state["page"], "Owner dashboard")
        self.assertEqual(app.session_state.filtered_state["owner_section"], "Tutors")
        self.assertTrue(any("published successfully" in item.value for item in app.success))

    def test_owner_can_delete_a_tutor_after_confirmation(self):
        owner = {"id": "owner-1", "email": "taleenalali5@gmail.com"}
        managed = {**self.tutor, "tutor_email": "layla@example.com", "active": True}
        with patch("auth.current_user", return_value=owner), patch("auth.is_owner", return_value=True), patch("backend.configuration_missing", return_value=[]), patch("backend.managed_tutors", return_value=[managed]), patch("backend.delete_tutor") as delete_mock:
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("Owner dashboard").run(timeout=20)
            next(item for item in app.checkbox if item.label.startswith("I understand that deleting")).set_value(True)
            self.button(app, "Delete tutor").click().run(timeout=20)
        self.assertFalse(app.exception)
        delete_mock.assert_called_once_with("tutor-1", owner)
        self.assertTrue(any("was deleted" in item.value for item in app.success))

    def test_owner_can_assign_tutor_dashboard_email(self):
        owner = {"id": "owner-1", "email": "taleenalali5@gmail.com"}
        managed = {**self.tutor, "tutor_email": "layla@example.com", "active": True, "deleted_at": None}
        with patch("auth.current_user", return_value=owner), patch("auth.is_owner", return_value=True), patch("backend.configuration_missing", return_value=[]), patch("backend.managed_tutors", return_value=[managed]), patch("backend.tutor_role_assignments", return_value=[]), patch("backend.assign_tutor_role") as assign_mock:
            app = AppTest.from_file("app.py").run(timeout=20)
            app.radio[0].set_value("Owner dashboard").run(timeout=20)
            next(item for item in app.radio if item.label == "Owner section").set_value("Tutor access").run(timeout=20)
            next(item for item in app.text_input if item.label == "Tutor account email").set_value("Layla@Example.com")
            self.button(app, "Assign Tutor role").click().run(timeout=20)
        self.assertFalse(app.exception)
        assign_mock.assert_called_once_with("tutor-1", "layla@example.com", owner)


if __name__ == "__main__":
    unittest.main()
