import io
import unittest

import pandas as pd

from backend.uploads import read_uploaded_dataframe


class UploadReaderTests(unittest.TestCase):
    def test_excel_reader_uses_first_nonempty_sheet(self):
        workbook = io.BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Cover", index=False)
            pd.DataFrame({"Region": ["North", "South"], "Revenue": [12, 21]}).to_excel(
                writer, sheet_name="Data", index=False
            )

        result = read_uploaded_dataframe("sales.xlsx", workbook.getvalue())

        self.assertEqual(result.shape, (2, 2))
        self.assertEqual(result["Revenue"].tolist(), [12, 21])

    def test_xlsx_file_reads_with_the_openpyxl_engine(self):
        workbook = io.BytesIO()
        pd.DataFrame({"Count": [3]}).to_excel(workbook, index=False, engine="openpyxl")

        result = read_uploaded_dataframe("report.xlsx", workbook.getvalue())

        self.assertEqual(result.loc[0, "Count"], 3)

    def test_workbook_without_data_sheets_gets_a_clear_error(self):
        workbook = io.BytesIO()
        pd.DataFrame().to_excel(workbook, engine="openpyxl", index=False)

        with self.assertRaisesRegex(ValueError, "no non-empty sheets"):
            read_uploaded_dataframe("empty.xlsx", workbook.getvalue())


if __name__ == "__main__":
    unittest.main()

