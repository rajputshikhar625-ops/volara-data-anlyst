import unittest

from streamlit.testing.v1 import AppTest
import pandas as pd

from backend.reporting import build_pdf_report


class FrontendSmokeTests(unittest.TestCase):
    def test_reports_page_renders_without_duplicate_export_buttons(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=30).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        app.session_state["page"] = "Reports"
        app.run()
        self.assertEqual(list(app.exception), [])

    def test_all_workspaces_render_after_loading_sample(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=30).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        for page in ["Dashboard", "Quick analysis", "Pivot table", "Data Lab", "Ask Volara", "Reports", "Connectors"]:
            app.session_state["page"] = page
            app.run()
            self.assertEqual(list(app.exception), [], f"{page} should render without errors")

    def test_dashboard_export_controls_and_theme_are_available(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=30).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        self.assertIn("Dashboard PDF", [button.label for button in app.get("download_button")])
        self.assertIn("Export chart", [button.label for button in app.get("download_button")])
        self.assertIn("Dark theme", [checkbox.label for checkbox in app.checkbox])
        app.checkbox[0].check().run()
        self.assertEqual(list(app.exception), [])

    def test_dashboard_pdf_is_a_valid_pdf_payload(self):
        content = build_pdf_report(pd.DataFrame({"Region": ["North"], "Revenue": [12]}), "sales")
        self.assertTrue(content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

