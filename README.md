# Volara Data Analyst

Volara Data Analyst is a beginner-friendly workspace for exploring files, building interactive dashboards, creating pivot tables, cleaning data, and asking questions in plain language. It pairs a FastAPI service with a Streamlit app. Core analysis works locally without an AI key.

## The V3 dashboard

The **Dashboard** workspace is the primary screen and follows the supplied Volara Report Designer V3 layout. Its ribbon provides Home, Insert, and View controls; the canvas has field and options panes; and its bottom page tabs switch between:

- **Overview** — KPI cards, summary charts, filters, and data chat.
- **Data table** — searchable and sortable data with row selection.
- **Dashboard** — the visual dashboard builder. Add column, bar, and donut charts, choose data/grouping/measure/calculation/width and an individual color for every chart, import another CSV as a dataset, or remove and clear charts.

Other workspaces remain available: Quick analysis, Pivot table, Data Lab, Ask Volara, Reports, and Connectors. Google Sheets and external database connections on the Connectors page are placeholders and are not enabled yet.

## Run on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and select **Add python.exe to PATH** during setup.
2. Download or extract this repository into a folder you can write to.
3. Double-click `RUN_VOLARA_DATA_ANALYST.bat` (the earlier `RUN_AURLEX_INSIGHTS.bat` is kept too).
4. On first launch, the launcher prepares dependencies and starts the API and app. Open http://127.0.0.1:8501.
5. Choose **Load sample dataset** to try the app without importing a file.

CSV and Excel files load into the local dashboard. Excel uploads read the first non-empty worksheet. If the API rejects an otherwise readable CSV or workbook, the dashboard keeps working with the locally loaded data and shows the backend's specific message. `.xlsx` uses `openpyxl`; legacy `.xls` files use `xlrd`.

The API is at http://127.0.0.1:8000 and its interactive docs are at http://127.0.0.1:8000/docs.

## Optional Gemini chat

AI answers need a private Gemini key. Copy `.env.example` to `.env` and add the key there. Keep `.env` private; it is excluded from Git. Local charts, pivots, cleaning, summaries, and exports work without the key.

## Run the checks

From the project folder, run:

```powershell
python -m unittest discover -s tests -v
```

The checks cover workspace rendering, the V3 report designer pages and chart builder, per-chart colors, de-duplicated ribbon controls, CSV/Excel reading, filters, pivot logic, PDF generation, and Gemini model fallback.

## Run manually

Create and install into a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Start the API in one terminal:

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the dashboard in another:

```powershell
$env:API_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

## Docker

Copy `.env.example` to `.env`, then run `docker compose up --build`. The dashboard is on port 8501 and the API is on port 8000.

