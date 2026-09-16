import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import auth


class AuthTests(unittest.TestCase):
    def test_sign_up_never_saves_an_unverified_session(self):
        client = MagicMock()
        client.auth.sign_up.return_value = SimpleNamespace(session=SimpleNamespace())
        with patch("auth._client", return_value=client), patch("auth._save_session") as save:
            auth.sign_up(" Student@Example.com ", "safe-password")
        client.auth.sign_up.assert_called_once_with({"email": "student@example.com", "password": "safe-password"})
        save.assert_not_called()

    def test_sign_in_rejects_an_unverified_email(self):
        client = MagicMock()
        user = SimpleNamespace(id="user-1", email="student@example.com", email_confirmed_at=None, confirmed_at=None)
        client.auth.sign_in_with_password.return_value = SimpleNamespace(session=SimpleNamespace(), user=user)
        with patch("auth._client", return_value=client), patch("auth._save_session") as save:
            with self.assertRaisesRegex(ValueError, "Confirm your email"):
                auth.sign_in("student@example.com", "safe-password")
        client.auth.sign_out.assert_called_once()
        save.assert_not_called()

    def test_sign_in_accepts_a_verified_email(self):
        client = MagicMock()
        session = SimpleNamespace(access_token="access", refresh_token="refresh")
        user = SimpleNamespace(id="user-1", email="student@example.com", email_confirmed_at="2026-01-01", confirmed_at=None)
        client.auth.sign_in_with_password.return_value = SimpleNamespace(session=session, user=user)
        with patch("auth._client", return_value=client), patch("auth._save_session") as save:
            result = auth.sign_in("student@example.com", "safe-password")
        self.assertEqual(result, {"id": "user-1", "email": "student@example.com"})
        save.assert_called_once_with(session)

    def test_current_user_restores_and_refreshes_saved_session(self):
        client = MagicMock()
        session = SimpleNamespace(access_token="access", refresh_token="refresh")
        user = SimpleNamespace(id="user-1", email="student@example.com", email_confirmed_at="2026-01-01", confirmed_at=None)
        client.auth.set_session.return_value = SimpleNamespace(session=session, user=user)
        with patch("auth._read_saved_session", return_value=("old-access", "saved-refresh")), patch("auth._client", return_value=client), patch("auth._save_session") as save, patch.dict(auth.st.session_state, {}, clear=True):
            result = auth.current_user()
        self.assertEqual(result, {"id": "user-1", "email": "student@example.com"})
        client.auth.set_session.assert_called_once_with("old-access", "saved-refresh")
        save.assert_called_once_with(session)

    def test_transient_restore_error_does_not_clear_saved_session(self):
        with patch("auth._read_saved_session", return_value=("access", "refresh")), patch("auth._client", side_effect=RuntimeError("network unavailable")), patch("auth._clear_session") as clear, patch.dict(auth.st.session_state, {}, clear=True):
            self.assertIsNone(auth.current_user())
        clear.assert_not_called()


if __name__ == "__main__":
    unittest.main()
