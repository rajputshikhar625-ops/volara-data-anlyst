"""Export helpers for portable Volara Data Analyst reports."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape


def build_pdf_report(dataframe, table_name=None):
    """Build a PDF snapshot with dataset details and a readable data sample."""
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Volara Data Analyst · Dashboard report", styles["Title"]),
        Paragraph(
            f"Dataset: {escape(str(table_name or 'Uploaded data'))} · "
            f"{len(dataframe):,} rows · {len(dataframe.columns):,} columns",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]
    headers = [str(column)[:80] for column in dataframe.columns[:10]]
    rows = [
        [str(value)[:80] for value in row]
        for row in dataframe.iloc[:30, :10].fillna("").values.tolist()
    ]
    table = Table([headers] + rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20242d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce1e8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f5f8")]),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return output.getvalue()

