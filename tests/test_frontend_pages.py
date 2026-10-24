import unittest

from streamlit.testing.v1 import AppTest


class FrontendSmokeTests(unittest.TestCase):
    def test_reports_page_renders_without_duplicate_export_buttons(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=30).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        app.session_state["page"] = "Reports"
        app.run()
        self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()

