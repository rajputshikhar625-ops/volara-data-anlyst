"""Shared, defensive readers for locally uploaded tabular files."""

from io import BytesIO
from pathlib import Path

import pandas as pd


def read_uploaded_dataframe(filename, contents):
    """Read supported tabular content, choosing the first non-empty Excel sheet."""
    suffix = Path(filename or "").suffix.lower()
    if not contents:
        raise ValueError("The selected file is empty.")
    source = BytesIO(contents)
    if suffix == ".csv":
        try:
            return pd.read_csv(source)
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(contents), encoding="latin1")
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"}:
        engine = "xlrd" if suffix == ".xls" else "openpyxl"
        sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine=engine)
        for dataframe in sheets.values():
            if not dataframe.empty and len(dataframe.columns):
                return dataframe
        raise ValueError("This Excel workbook has no non-empty sheets.")
    if suffix == ".parquet":
        return pd.read_parquet(BytesIO(contents))
    if suffix == ".json":
        return pd.read_json(BytesIO(contents))
    return None

