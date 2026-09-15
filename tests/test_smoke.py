import unittest

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Streamlit testing support is unavailable")
class SmokeTests(unittest.TestCase):
    def test_home_renders_without_credentials(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Students helping students grow.")
        self.assertTrue(any("Setup is not finished" in warning.value for warning in app.warning))

    def test_public_navigation_and_missing_backend_error(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.header[0].value, "Find a tutor")
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("database connection" in error.value.lower() for error in app.error))

    def test_account_page_renders(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        app.radio[0].set_value("My account").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.header[0].value, "My account")
        self.assertEqual([tab.label for tab in app.tabs], ["Sign in", "Create account", "Reset password"])


if __name__ == "__main__":
    unittest.main()
