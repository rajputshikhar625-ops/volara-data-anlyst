"""Small dataframe helpers used by the beginner-friendly analysis screens."""

import pandas as pd


AGGREGATIONS = {
    "Sum": "sum",
    "Average": "mean",
    "Count": "count",
    "Lowest": "min",
    "Highest": "max",
}


def build_pivot(dataframe, rows, columns=None, values=None, aggregation="Sum"):
    """Build a pivot-style table from simple field and summary choices."""
    if rows not in dataframe.columns:
        raise ValueError("Choose a valid field for the rows.")
    if columns and columns not in dataframe.columns:
        raise ValueError("Choose a valid field for the columns.")
    if columns == rows:
        raise ValueError("Choose a different field for columns, or select No columns.")
    if values and values not in dataframe.columns:
        raise ValueError("Choose a valid number field.")
    if aggregation not in AGGREGATIONS:
        raise ValueError("Choose Sum, Average, Count, Lowest, or Highest.")
    if aggregation != "Count" and not values:
        raise ValueError("Choose a number field to summarize.")

    working = dataframe.copy()
    for group_field in [rows, columns]:
        if group_field:
            working[group_field] = working[group_field].fillna("(Blank)")

    if not values and aggregation == "Count":
        if columns is None:
            result = working.groupby(rows).size().to_frame("Count")
        else:
            result = (
                working.groupby([rows, columns])
                .size()
                .unstack(columns, fill_value=0)
            )
    else:
        result = working.pivot_table(
            index=rows,
            columns=columns,
            values=values,
            aggfunc=AGGREGATIONS[aggregation],
            fill_value=0,
            dropna=True,
        )
    return result


def summarize_dataframe(dataframe):
    """Return simple counts and numeric summaries for a dataset."""
    numeric = dataframe.select_dtypes(include="number")
    numeric_summary = {}
    for column in numeric.columns:
        series = numeric[column].dropna()
        if series.empty:
            continue
        numeric_summary[column] = {
            "total": float(series.sum()),
            "average": float(series.mean()),
            "highest": float(series.max()),
            "lowest": float(series.min()),
        }
    return {
        "rows": int(len(dataframe)),
        "columns": int(len(dataframe.columns)),
        "missing_cells": int(dataframe.isna().sum().sum()),
        "duplicate_rows": int(dataframe.duplicated().sum()),
        "numeric": numeric_summary,
    }




def make_basic_answer(question, dataframe, category, metric):
    """Answer common beginner questions using only the values already in memory."""
    answer = f"Your file has {len(dataframe):,} rows and {len(dataframe.columns)} columns."
    if metric in dataframe.columns and pd.api.types.is_numeric_dtype(dataframe[metric]):
        values = dataframe[metric].dropna()
        if not values.empty:
            answer += f"\n\n{metric} adds up to {values.sum():,.2f} and averages {values.mean():,.2f}."
            if category in dataframe.columns:
                groups = dataframe.groupby(category, dropna=False)[metric].sum().sort_values(ascending=False).head(5)
                answer += "\n\nLargest groups by " + metric + ":\n" + "\n".join(
                    f"{label}: {value:,.2f}" for label, value in groups.items()
                )
    elif category in dataframe.columns:
        counts = dataframe[category].fillna("(Blank)").astype(str).value_counts().head(5)
        if not counts.empty:
            answer += "\n\nGroups with the most rows:\n" + "\n".join(
                f"{label}: {count:,} rows" for label, count in counts.items()
            )
    if not question.strip():
        return answer
    return answer

