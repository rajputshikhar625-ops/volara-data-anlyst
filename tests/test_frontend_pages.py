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
        app = AppTest.from_file("frontend/app.py", default_timeout=90).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        self.assertIn("PDF", [button.label for button in app.get("download_button")])
        app.radio(key="dl_chart_type").set_value("Pie chart").run()
        app.radio(key="report_right_tab").set_value("Filters").run()
        app.selectbox(key="dashboard_filter_column").set_value("region").run()
        app.multiselect(key="dashboard_filter_values").select("North").run()
        self.assertTrue(any("2 filtered rows" in str(item.value) for item in app.markdown))
        app.radio(key="report_ribbon").set_value("View").run()
        self.assertIn("Dark theme", [checkbox.label for checkbox in app.checkbox])
        next(box for box in app.checkbox if box.label == "Dark theme").check().run()
        self.assertEqual(list(app.exception), [])
        app.radio(key="report_page").set_value("Dashboard").run()
        next(button for button in app.button if button.label == "Clear charts").click().run()
        self.assertEqual(len(app.session_state["dashboard_charts"]), 0)
        starting_charts = len(app.session_state["dashboard_charts"])
        next(button for button in app.button if button.label == "+ Column chart").click().run()
        self.assertEqual(len(app.session_state["dashboard_charts"]), starting_charts + 1)
        self.assertEqual(list(app.exception), [])

    def test_report_designer_has_three_pages_and_dashboard_builder(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=90).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        self.assertEqual(app.radio(key="report_page").options, ["Overview", "Data table", "Dashboard"])
        app.radio(key="report_page").set_value("Data table").run()
        self.assertEqual(list(app.exception), [])
        app.radio(key="report_page").set_value("Dashboard").run()
        self.assertIn("+ Donut chart", [button.label for button in app.button])
        self.assertIn("PDF", [button.label for button in app.get("download_button")])

    def test_dashboard_chart_tiles_have_independent_colors(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=90).run()
        next(button for button in app.button if button.label == "Load sample dataset").click().run()
        app.radio(key="report_page").set_value("Dashboard").run()
        colors = {picker.key: picker.value for picker in app.get("color_picker") if picker.key.startswith("builder_color_")}
        self.assertEqual(len(colors), 3)
        self.assertEqual(len(set(colors.values())), 3)

    def test_home_ribbon_has_no_duplicate_select_all_button(self):
        app = AppTest.from_file("frontend/app.py", default_timeout=60).run()
        self.assertNotIn("Select all", [button.label for button in app.button])
        self.assertIn("Select all", next(select for select in app.selectbox if select.key == "designer_selection_action").options)

    def test_dashboard_pdf_is_a_valid_pdf_payload(self):
        content = build_pdf_report(pd.DataFrame({"Region": ["North"], "Revenue": [12]}), "sales")
        self.assertTrue(content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

