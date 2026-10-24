# Aurlex Insights v2.1

This package uses the v2.1 full-stack app: a FastAPI backend with a Streamlit dashboard. It has more features than the older ZIP and the single-file edition.

## Compare the versions

- `aurlex-insights.zip` (older): basic upload, analysis, and query flow; one backend module and one frontend app.
- `aurlex-insights-v2.1.zip` (chosen): adds multi-file workflows, data cleaning, filtering, reporting, and standalone mode when the API is unavailable. It contains the full backend and current frontend. The Connectors screen is a placeholder; Google Sheets and database connectors are not wired into the dashboard yet.
- `Aurlex-Single.py`: one-file Streamlit edition, simpler to start, but it does not include the full backend workflow.

## Run on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and select **Add python.exe to PATH** during setup.
2. Extract this ZIP to a folder you can write to.
3. Double-click `RUN_AURLEX_INSIGHTS.bat`.
4. On first launch, it creates a local Python environment and installs the dependencies. It then opens the dashboard at http://localhost:8501.

The dashboard uses a simple, guided layout: add a file on the left, then use **Quick analysis**, **Pivot table**, **Data Lab**, or the chat to explore it. Click **Load sample dataset** to try the tools right away.

- **Quick analysis** explains row counts, blank cells, repeated rows, and simple number summaries.
- **Pivot table** lets you choose row groups, optional column groups, and totals, averages, counts, lows, or highs. Download the result as CSV.
- **Data chat** includes starter questions and remembers recent turns so follow-up questions make sense.
- **Data Lab** keeps file cleaning, sorting, filtering, and chart building in one screen.

The API runs at http://localhost:8000 and its interactive docs are at http://localhost:8000/docs. The Gemini AI key is optional; without it, charts, pivot tables, cleaning, exports, and quick summaries still work. The chat uses Gemini when a key is configured.

To enable Gemini, copy `.env.example` to `.env` and add your key. The default model is `gemini-3.8-flash`; you can change `GEMINI_MODEL` in `.env`. Keep `.env` private; it is excluded from Git.

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





