import unittest

import pandas as pd

from backend.analytics import build_pivot, summarize_dataframe, make_basic_answer


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "Region": ["North", "North", "South"],
                "Quarter": ["Q1", "Q2", "Q1"],
                "Sales": [10, 15, 7],
                "Orders": [1, 2, 1],
            }
        )

    def test_build_pivot_sums_values_by_two_groups(self):
        result = build_pivot(self.data, rows="Region", columns="Quarter", values="Sales", aggregation="Sum")
        self.assertEqual(result.loc["North", "Q1"], 10)
        self.assertEqual(result.loc["North", "Q2"], 15)
        self.assertEqual(result.loc["South", "Q1"], 7)

    def test_build_pivot_counts_rows_without_a_value_column(self):
        result = build_pivot(self.data, rows="Region", columns=None, values=None, aggregation="Count")
        self.assertEqual(result.loc["North", "Count"], 2)
        self.assertEqual(result.loc["South", "Count"], 1)

    def test_summarize_dataframe_reports_easy_to_read_health_counts(self):
        frame = self.data.copy()
        frame.loc[0, "Sales"] = None
        result = summarize_dataframe(frame)
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["columns"], 4)
        self.assertEqual(result["missing_cells"], 1)
        self.assertEqual(result["duplicate_rows"], 0)


    def test_build_pivot_keeps_missing_group_values_visible(self):
        frame = pd.DataFrame({"Region": ["North", None], "Quarter": ["Q1", None], "Sales": [4, 6]})
        result = build_pivot(frame, rows="Region", columns="Quarter", values="Sales", aggregation="Sum")
        self.assertEqual(result.loc["(Blank)", "(Blank)"], 6)
    def test_basic_answer_finds_the_largest_group_without_ai(self):
        result = make_basic_answer("Which region has the most rows?", self.data, "Region", "Rows")
        self.assertIn("North", result)
        self.assertIn("2", result)
if __name__ == "__main__":
    unittest.main()



