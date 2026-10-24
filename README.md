# Volara Data Analyst

Volara Data Analyst is a friendly, local-first workspace for exploring files, building dashboards, creating pivot tables, cleaning data, and asking questions in plain language. It pairs a FastAPI service with a Streamlit dashboard and keeps core analysis available when the API or AI service is offline.

## Compare the versions

- Existing Aurlex files and workflows remain available in this project; Volara Data Analyst is the current product name.
- The dashboard includes visual summaries, KPI cards, chart filters, a fields list, pivot tables, data cleaning, chat, and Excel, CSV, SQL, PDF, and chart exports.
- The Connectors screen is still a placeholder; Google Sheets and database connections are not wired in yet.

## Run on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and select **Add python.exe to PATH** during setup.
2. Extract this ZIP to a folder you can write to.
3. Double-click `RUN_VOLARA_DATA_ANALYST.bat` (the older `RUN_AURLEX_INSIGHTS.bat` is also kept).
4. On first launch, it creates a local Python environment and installs the dependencies. It then opens the dashboard at http://localhost:8501.

The dashboard uses a guided report layout: add a file on the left, then use **Dashboard**, **Quick analysis**, **Pivot table**, **Data Lab**, or **Ask Volara** to explore it. Click **Load sample dataset** to try the tools right away. The Dashboard page includes headline data checks, chart controls, an interactive filter, field types, and a chat assistant.

- **Quick analysis** explains row counts, blank cells, repeated rows, and simple number summaries.
- **Pivot table** lets you choose row groups, optional column groups, and totals, averages, counts, lows, or highs. Download the result as CSV.
- **Data chat** includes starter questions and remembers recent turns so follow-up questions make sense. AI answers require a private Gemini key; local analysis still works without it.
- **Data Lab** keeps file cleaning, sorting, filtering, and chart building in one screen.
- **Dashboard PDF** downloads a shareable snapshot with dataset details and a sample of its rows.

The API runs at http://localhost:8000 and its interactive docs are at http://localhost:8000/docs. The Gemini AI key is optional; without it, charts, pivot tables, cleaning, exports, and quick summaries still work. The chat uses Gemini when a key is configured.

To enable Gemini, copy `.env.example` to `.env` and add your key. Keep `.env` private; it is excluded from Git.

## Run manually

From the extracted folder, install dependencies and start the services in separate terminals:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
$env:API_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

## Docker

Copy `.env.example` to `.env`, then run `docker compose up --build`. The dashboard is on port 8501 and the API is on port 8000.





