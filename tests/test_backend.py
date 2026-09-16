import unittest

from unittest.mock import patch

from backend import assign_tutor_role, friendly_error, require_tutor


class BackendErrorTests(unittest.TestCase):
    def test_permission_error_does_not_claim_the_session_expired(self):
        message = friendly_error(RuntimeError("row-level security policy denied this request"))
        self.assertIn("permission", message.lower())
        self.assertNotIn("expired", message.lower())

    def test_actual_expired_jwt_reports_expiration(self):
        self.assertIn("expired", friendly_error(RuntimeError("JWT expired")).lower())

    def test_unassigned_user_cannot_use_tutor_operations(self):
        with patch("backend.tutor_assignment", return_value=None):
            with self.assertRaisesRegex(PermissionError, "Tutor access"):
                require_tutor({"id": "student", "email": "student@example.com"})

    def test_non_owner_cannot_assign_tutor_role(self):
        with self.assertRaisesRegex(PermissionError, "Owner access"):
            assign_tutor_role("tutor-1", "tutor@example.com", {"id": "student", "email": "student@example.com"})


if __name__ == "__main__":
    unittest.main()
