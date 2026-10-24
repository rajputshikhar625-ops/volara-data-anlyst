import html
import io
import os
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analytics import build_pivot, make_basic_answer, summarize_dataframe
from backend.reporting import build_pdf_report
from backend.uploads import read_uploaded_dataframe

st.set_page_config(
    page_title="Volara Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
      --dl-bg: #f3f4f7;
      --dl-panel: #ffffff;
      --dl-line: #e3e6ec;
      --dl-text: #1f2430;
      --dl-muted: #6b7280;
      --dl-accent: #f2c811;
      --dl-blue: #2563eb;
      --dl-green: #16a34a;
    }
    html, body, [class*="css"] { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
    [data-testid="stAppViewContainer"], .stApp { background: var(--dl-bg); color: var(--dl-text); }
    [data-testid="stHeader"] { background: transparent; height: 0; }
    [data-testid="stToolbar"] { right: 1rem; }
    .main .block-container { max-width: 100%; padding: 1rem 1.15rem 1.5rem; }
    [data-testid="stSidebar"] {
      background: var(--dl-panel);
      border-right: 1px solid var(--dl-line);
      min-width: 248px;
      max-width: 248px;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--dl-text); }
    .dl-brand { display:flex; align-items:center; gap:10px; padding:7px 2px 17px; border-bottom:1px solid var(--dl-line); margin-bottom:18px; }
    .dl-mark { width:30px; height:30px; display:grid; place-items:center; border-radius:7px; background:var(--dl-accent); color:#1f2430; font-weight:800; }
    .dl-brand-name { font-weight:700; font-size:15px; color:var(--dl-text); }
    .dl-brand-sub { color:var(--dl-muted); font-size:11px; margin-top:2px; }
    .dl-section { margin:14px 0 8px; color:var(--dl-muted); text-transform:uppercase; font-size:11px; font-weight:700; letter-spacing:.06em; }
    .dl-topbar { display:flex; justify-content:space-between; align-items:center; padding:2px 0 10px; border-bottom:1px solid var(--dl-line); margin-bottom:14px; }
    .dl-title { font-size:20px; font-weight:700; color:var(--dl-text); }
    .dl-subtitle { color:var(--dl-muted); font-size:12px; margin-top:3px; }
    .dl-card { background:var(--dl-panel); border:1px solid var(--dl-line); border-radius:10px; padding:14px 16px; }
    .dl-card-title { color:var(--dl-text); font-size:14px; font-weight:650; }
    .dl-muted { color:var(--dl-muted); font-size:12px; }
    .dl-chat-head { padding:8px 0 12px; border-bottom:1px solid var(--dl-line); font-weight:700; font-size:15px; }
    .dl-msg { padding:10px 12px; border-radius:10px; margin:8px 0; max-width:94%; white-space:pre-wrap; font-size:13px; line-height:1.45; }
    .dl-msg.bot { background:#f3f4f7; color:var(--dl-text); margin-right:auto; }
    .dl-msg.user { background:var(--dl-blue); color:#fff; margin-left:auto; }
    .stButton > button, .stDownloadButton > button {
      border:1px solid var(--dl-line); background:#fff; color:var(--dl-text);
      border-radius:7px; min-height:36px; font-weight:550;
    }
    .stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--dl-blue); color:var(--dl-blue); }
    button[kind="primary"] { background:#1f2430 !important; color:#fff !important; border-color:#1f2430 !important; }
    .dl-table-scroll { overflow:auto; max-height:340px; border:1px solid var(--dl-line); border-radius:8px; background:#fff; }
    .dl-data-table { width:100%; border-collapse:collapse; font-size:12px; color:var(--dl-text); }
    .dl-data-table th { position:sticky; top:0; background:#f8f9fb; text-align:left; font-weight:650; }
    .dl-data-table th, .dl-data-table td { padding:7px 10px; border-bottom:1px solid var(--dl-line); white-space:nowrap; }
    .dl-data-table tr:nth-child(even) { background:#fafbfc; }
    div[data-testid="stPlotlyChart"] { border:1px solid var(--dl-line); border-radius:9px; overflow:hidden; background:#fff; padding:5px; }
    div[data-testid="stAlert"] { border-radius:8px; }
    @media (max-width: 900px) {
      .main .block-container { padding: .75rem; }
      [data-testid="stSidebar"] { min-width: 220px; max-width: 220px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULTS = {
    "df": None,
    "table_name": None,
    "charts": [],
    "workspace": "Personal",
    "page": "Dashboard",
    "disambig_ctx": {},
    "source_files": [],
    "messages": [
        {
            "role": "assistant",
            "content": "Hi! Load a dataset, choose a chart type, and ask me about your data.",
        }
    ],
    "row_selection_default": True,
    "loaded_upload_fingerprint": None,
    "dark_mode": False,
    "report_ribbon": "Home",
    "report_page": "Overview",
    "report_right_tab": "Visualize",
    "report_show_fields": True,
    "report_show_right": True,
    "report_selected_rows": [],
    "report_select_all": True,
    "report_selection_action": None,
    "dashboard_filter_column": "All fields",
    "dashboard_filter_values": [],
    "dashboard_datasets": {},
    "dashboard_charts": [],
    "dashboard_initialized": False,
    "builder_upload_fingerprint": None,
    "overview_chart_color": "#2563eb",
    "lab_chart_color": "#2563eb",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value.copy() if isinstance(value, (list, dict)) else value


def api_status():
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=1.2)
        if response.ok:
            return response.json()
    except requests.RequestException:
        pass
    return None


def read_uploaded(file_obj):
    return read_uploaded_dataframe(file_obj.name, file_obj.getvalue())


def clear_row_selection():
    st.session_state.pop("datalens_table_editor", None)
    st.session_state["row_selection_default"] = True


def _default_dashboard_charts(dataframe, dataset_name):
    numeric = dataframe.select_dtypes(include="number").columns.tolist()
    categories = [column for column in dataframe.columns if column not in numeric]
    group = categories[0] if categories else (dataframe.columns[0] if len(dataframe.columns) else None)
    measure = numeric[0] if numeric else ""
    charts = []
    for index, chart_type in enumerate(("column", "bar", "donut"), start=1):
        title = f"{chart_type.title()} chart · {group}" if group else f"{chart_type.title()} chart"
        charts.append({
            "id": index,
            "title": title,
            "dataset": dataset_name,
            "type": chart_type,
            "group": group,
            "measure": measure,
            "aggregation": "Sum" if measure else "Count",
            "color": ["#2563eb", "#16a34a", "#f59e0b"][index - 1],
            "span": 6,
        })
    return charts


def set_dataset(dataframe, table_name=None, sources=None, fingerprint=None):
    st.session_state.df = dataframe.reset_index(drop=True)
    st.session_state.table_name = table_name or "local_dataset"
    st.session_state.source_files = sources or []
    st.session_state.loaded_upload_fingerprint = fingerprint
    dataset_name = str(st.session_state.table_name)
    st.session_state.dashboard_datasets[dataset_name] = st.session_state.df.copy()
    if not st.session_state.dashboard_charts and not st.session_state.dashboard_initialized:
        st.session_state.dashboard_charts = _default_dashboard_charts(st.session_state.df, dataset_name)
        st.session_state.dashboard_initialized = True
    st.session_state.report_selected_rows = list(range(len(st.session_state.df)))
    st.session_state.report_select_all = True
    clear_row_selection()


def backend_upload(file_obj):
    files = {"file": (file_obj.name, file_obj.getvalue(), file_obj.type or "application/octet-stream")}
    response = requests.post(f"{API_URL}/api/upload", files=files, timeout=35)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise requests.HTTPError(f"Upload API returned {response.status_code}: {detail}", response=response)
    return response.json()


def backend_multi_upload(files, merge_how):
    payload = [("files", (file.name, file.getvalue(), file.type or "application/octet-stream")) for file in files]
    response = requests.post(
        f"{API_URL}/api/upload-multi?merge_how={merge_how}",
        files=payload,
        timeout=45,
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise requests.HTTPError(f"Multi-file upload API returned {response.status_code}: {detail}", response=response)
    return response.json()


def load_sample(api_health):
    sample_path = ROOT / "sample_sales.csv"
    dataframe = pd.read_csv(sample_path)
    table_name = "sample_sales"
    if api_health:
        try:
            with sample_path.open("rb") as sample:
                result = requests.post(
                    f"{API_URL}/api/upload",
                    files={"file": ("sample_sales.csv", sample, "text/csv")},
                    timeout=20,
                )
            if result.ok:
                table_name = result.json()["table_name"]
        except requests.RequestException:
            pass
    set_dataset(dataframe, table_name, ["sample_sales.csv"], ("sample",))
    st.toast("Sample sales data loaded")


def answer_locally(question, dataframe, category, metric, ai_busy=False):
    if dataframe is None:
        return "Upload a file or load the sample dataset first."
    response = make_basic_answer(question, dataframe, category, metric)
    if ai_busy:
        response += "\n\nGemini is busy right now, so this quick answer uses the data on this screen."
    else:
        response += "\n\nAdd a Gemini key to ask open-ended questions about your data."
    return response

def answer_with_ai(question, dataframe, category, metric, api_health, conversation_history=None):
    if dataframe is None:
        return "Upload a file or load the sample dataset first."
    if not api_health or not api_health.get("ai_enabled") or not st.session_state.table_name:
        return answer_locally(question, dataframe, category, metric)
    try:
        response = requests.post(
            f"{API_URL}/api/ai-query",
            json={
                "query": question,
                "table_name": st.session_state.table_name,
                "disambiguation_context": st.session_state.disambig_ctx,
                "chat_history": conversation_history or [],
            },
            timeout=45,
        )
        result = response.json()
        if response.ok and result.get("status") == "needs_clarification":
            return "\n".join(result.get("questions", ["Please clarify the query."]))
        if response.ok:
            insight = result.get("insight", "I found an answer.")
            rows = result.get("data", [])
            if rows:
                answer_table = pd.DataFrame(rows).head(8).to_string(index=False)
                return f"{insight}\n\nHere is what I found:\n{answer_table}"
            return insight
        detail = result.get("detail", response.text)
        if "Gemini is busy or unavailable right now" in detail:
            return answer_locally(question, dataframe, category, metric, ai_busy=True)
        return detail
    except requests.RequestException as exc:
        return f"Could not reach the analysis API: {exc}"


def render_downloads(dataframe, table_name, key_prefix="exports"):
    if dataframe is None:
        st.caption("Load data to enable exports.")
        return
    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Data")
        numeric = dataframe.select_dtypes(include="number")
        if not numeric.empty:
            numeric.describe().to_excel(writer, sheet_name="Summary")
    safe_name = table_name if table_name and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name) else "uploaded_data"
    export_cols = ", ".join(f'"{column}"' for column in dataframe.columns)
    sql_text = f'SELECT {export_cols} FROM "{safe_name}";\n'
    pdf_bytes = build_pdf_report(dataframe, table_name)
    buttons = st.columns(4, gap="small")
    compact = key_prefix == "top"
    with buttons[0]:
        st.download_button("Excel" if compact else "Export Excel", excel_buffer.getvalue(), "aurlex_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"{key_prefix}_excel")
    with buttons[1]:
        st.download_button("CSV" if compact else "Export CSV", csv_bytes, "aurlex_data.csv", "text/csv", use_container_width=True, key=f"{key_prefix}_csv")
    with buttons[2]:
        st.download_button("SQL" if compact else "Export SQL", sql_text, "aurlex_query.sql", "text/plain", use_container_width=True, key=f"{key_prefix}_sql")
    with buttons[3]:
        st.download_button("PDF" if compact else "Dashboard PDF", pdf_bytes, "volara_dashboard.pdf", "application/pdf", use_container_width=True, key=f"{key_prefix}_pdf")


def add_dashboard_chart(chart_type, dataset_name=None):
    datasets = st.session_state.dashboard_datasets
    if dataset_name is None:
        dataset_name = str(st.session_state.table_name or next(iter(datasets), ""))
    dataframe = datasets.get(dataset_name, st.session_state.df)
    if dataframe is None or dataframe.empty or not len(dataframe.columns):
        st.warning("Load a dataset before adding a chart.")
        return
    numeric = dataframe.select_dtypes(include="number").columns.tolist()
    categories = [column for column in dataframe.columns if column not in numeric]
    group = categories[0] if categories else dataframe.columns[0]
    measure = numeric[0] if numeric else ""
    next_id = max([int(chart.get("id", 0)) for chart in st.session_state.dashboard_charts] + [0]) + 1
    st.session_state.dashboard_charts.append({
        "id": next_id, "title": f"{chart_type.title()} chart · {group}", "dataset": dataset_name,
        "type": chart_type, "group": group, "measure": measure,
        "aggregation": "Sum" if measure else "Count", "span": 6,
        "color": ["#2563eb", "#16a34a", "#f59e0b"][next_id % 3],
    })
    st.session_state.report_page = "Dashboard"


def _aggregate_dashboard_chart(dataframe, group, measure, aggregation):
    if dataframe is None or dataframe.empty or group not in dataframe.columns:
        return pd.DataFrame(columns=[group or "Group", "value"])
    if aggregation == "Count" or not measure or measure not in dataframe.columns:
        result = dataframe.groupby(group, dropna=False).size().rename("value").reset_index()
    elif aggregation == "Average":
        result = dataframe.groupby(group, dropna=False)[measure].mean().rename("value").reset_index()
    else:
        result = dataframe.groupby(group, dropna=False)[measure].sum().rename("value").reset_index()
    result[group] = result[group].fillna("(Blank)").astype(str)
    return result.sort_values("value", ascending=False).head(20)


def _dashboard_chart_figure(dataframe, chart_type, group, measure, aggregation, height=310, accent_color="#2563eb"):
    grouped = _aggregate_dashboard_chart(dataframe, group, measure, aggregation)
    if grouped.empty:
        return None
    label = measure if aggregation != "Count" and measure else "Rows"
    if chart_type in {"donut", "Pie chart"}:
        palette = [accent_color] + [color for color in px.colors.qualitative.Safe if color.lower() != accent_color.lower()]
        figure = px.pie(grouped, names=group, values="value", hole=0.48, color_discrete_sequence=palette)
    elif chart_type in {"bar", "Horizontal chart"}:
        figure = px.bar(grouped.sort_values("value"), x="value", y=group, orientation="h", color_discrete_sequence=[accent_color])
    else:
        figure = px.bar(grouped, x=group, y="value", color_discrete_sequence=[accent_color])
    figure.update_layout(
        template="plotly_white", paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", height=height,
        margin=dict(l=12, r=12, t=22, b=18), showlegend=chart_type in {"donut", "Pie chart"},
        xaxis_title=None if chart_type in {"bar", "Horizontal chart"} else label,
        yaxis_title=group if chart_type in {"bar", "Horizontal chart"} else None, legend_title_text="",
    )
    figure.update_xaxes(showgrid=True, gridcolor="#e3e6ec", zeroline=False)
    figure.update_yaxes(showgrid=False, zeroline=False)
    return figure


def _render_builder_chart(spec, datasets, filter_column=None, filter_values=None):
    chart_id = int(spec["id"])
    with st.container():
        title = st.text_input("Title", value=spec.get("title", "Untitled chart"), key=f"builder_title_{chart_id}")
        dataset_names = list(datasets)
        if not dataset_names:
            st.info("Add a dataset to configure this chart.")
            return
        saved_dataset = spec.get("dataset")
        initial_dataset = saved_dataset if saved_dataset in dataset_names else dataset_names[0]
        dataset_name = st.selectbox("Data", dataset_names, index=dataset_names.index(initial_dataset), key=f"builder_dataset_{chart_id}")
        dataframe = datasets[dataset_name]
        available = dataframe.copy()
        if filter_column and filter_column in available.columns and filter_values:
            available = available[available[filter_column].astype(str).isin(filter_values)]
        numeric = dataframe.select_dtypes(include="number").columns.tolist()
        categories = [column for column in dataframe.columns if column not in numeric]
        group_options = categories or dataframe.columns.tolist()
        if not group_options:
            st.info("This dataset has no columns to chart.")
            return
        saved_group = spec.get("group")
        initial_group = saved_group if saved_group in group_options else group_options[0]
        group = st.selectbox("Group by", group_options, index=group_options.index(initial_group), key=f"builder_group_{chart_id}_{dataset_name}")
        chart_types = {"Column": "column", "Bar": "bar", "Pie / donut": "donut"}
        selected_type = spec.get("type", "column")
        type_label = next((label for label, value in chart_types.items() if value == selected_type), "Column")
        chart_label = st.selectbox("Chart", list(chart_types), index=list(chart_types).index(type_label), key=f"builder_type_{chart_id}")
        chart_type = chart_types[chart_label]
        measures = ["Count"] + numeric
        saved_measure = spec.get("measure") or "Count"
        initial_measure = saved_measure if saved_measure in measures else measures[0]
        measure = st.selectbox("Measure", measures, index=measures.index(initial_measure), key=f"builder_measure_{chart_id}_{dataset_name}")
        agg_options = ["Count"] if measure == "Count" else ["Sum", "Average", "Count"]
        saved_agg = spec.get("aggregation", "Sum")
        aggregation = st.selectbox("Calculate", agg_options, index=agg_options.index(saved_agg) if saved_agg in agg_options else 0, key=f"builder_agg_{chart_id}_{dataset_name}")
        width_labels = {"4 of 12": 4, "6 of 12": 6, "12 of 12": 12}
        initial_span = spec.get("span", 6)
        initial_width = next((label for label, value in width_labels.items() if value == initial_span), "6 of 12")
        width_label = st.selectbox("Width", list(width_labels), index=list(width_labels).index(initial_width), key=f"builder_span_{chart_id}")
        span = width_labels[width_label]
        accent_color = st.color_picker("Chart color", value=spec.get("color", "#2563eb"), key=f"builder_color_{chart_id}")
        spec.update({"title": title, "dataset": dataset_name, "group": group, "type": chart_type,
                     "measure": "" if measure == "Count" else measure, "aggregation": aggregation, "span": span, "color": accent_color})
        chart_frame = available
        figure = _dashboard_chart_figure(chart_frame, chart_type, group, "" if measure == "Count" else measure, aggregation, accent_color=accent_color)
        if figure is not None:
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False}, key=f"builder_plot_{chart_id}")
            st.caption(f"{len(chart_frame):,} rows · {aggregation} · {group}")
            st.download_button("Export chart", figure.to_html(full_html=True, include_plotlyjs="cdn"), f"volara_chart_{chart_id}.html", "text/html", key=f"builder_export_{chart_id}")
        else:
            st.info("No rows match the current filters.")
        if st.button("Remove chart", key=f"builder_remove_{chart_id}"):
            st.session_state.dashboard_charts = [chart for chart in st.session_state.dashboard_charts if int(chart["id"]) != chart_id]
            st.rerun()


def _render_report_chat(dataframe, category, metric, api_health):
    st.markdown("##### Ask about this report")
    st.caption("Ask a question about the data on this canvas.")
    for message in st.session_state.messages[-6:]:
        role = "You" if message.get("role") == "user" else "Volara"
        st.markdown(f"**{role}:** {html.escape(str(message.get('content', '')))}")
    with st.form("report_designer_chat", clear_on_submit=True):
        question = st.text_input("Ask Volara", placeholder="Ask about this data…", label_visibility="collapsed")
        send = st.form_submit_button("Send", use_container_width=True, type="primary")
    if send and question.strip():
        history = list(st.session_state.messages[-6:])
        st.session_state.messages.append({"role": "user", "content": question})
        answer = answer_with_ai(question, dataframe, category, metric, api_health, history)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()


def render_report_designer(dataframe, table_name, api_health):
    """Primary Volara report designer; its third page is the editable chart builder."""
    st.markdown("## Volara Data Analyst <span style='color:#2563eb'>· Report Designer</span>", unsafe_allow_html=True)
    ribbon = st.radio("Report ribbon", ["Home", "Insert", "View"], horizontal=True, key="report_ribbon", label_visibility="collapsed")
    if ribbon == "Home":
        actions = st.columns([1, 1, 2.6], gap="small")
        with actions[0]:
            if st.button("Sample data", use_container_width=True, key="designer_sample"):
                load_sample(api_health)
                st.rerun()
        with actions[1]:
            action = st.selectbox("Selection", ["Select all", "Clear", "Invert"], key="designer_selection_action")
            if st.button("Apply", use_container_width=True, key="designer_apply_selection"):
                st.session_state.report_selection_action = {"Select all": "all", "Clear": "none", "Invert": "invert"}[action]
        with actions[2]:
            import_file = st.file_uploader("Import CSV", type=["csv"], key="designer_import_csv", label_visibility="collapsed")
            if import_file:
                fingerprint = (import_file.name, len(import_file.getvalue()))
                if fingerprint != st.session_state.get("designer_import_fingerprint"):
                    imported = read_uploaded(import_file)
                    if imported is not None:
                        set_dataset(imported, Path(import_file.name).stem, [import_file.name], fingerprint)
                        st.session_state.designer_import_fingerprint = fingerprint
                        st.rerun()
    elif ribbon == "Insert":
        inserts = st.columns(6, gap="small")
        for column, chart_type, label in zip(inserts[:3], ["column", "bar", "donut"], ["+ Column chart", "+ Bar chart", "+ Donut chart"]):
            with column:
                if st.button(label, use_container_width=True, key=f"insert_{chart_type}"):
                    add_dashboard_chart(chart_type)
        for column, report_page, label in zip(inserts[3:], ["Overview", "Data table", "Dashboard"], ["KPI cards", "Data table", "Dashboard"]):
            with column:
                if st.button(label, use_container_width=True, key=f"insert_page_{report_page}"):
                    st.session_state.report_page = report_page
    else:
        view_cols = st.columns(3, gap="small")
        with view_cols[0]:
            st.checkbox("Fields pane", key="report_show_fields")
        with view_cols[1]:
            st.checkbox("Right pane", key="report_show_right")
        with view_cols[2]:
            st.checkbox("Dark theme", key="dark_mode")

    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        :root { --dl-bg:#17191f !important; --dl-panel:#22252d !important; --dl-line:#373b46 !important; --dl-text:#edf0f6 !important; --dl-muted:#a4abba !important; }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp { background-color:#17191f !important; color:#edf0f6 !important; }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] { background-color:#22252d !important; }
        .stButton > button, .stDownloadButton > button, [data-baseweb="select"] > div, input, textarea { background:#2c303a !important; color:#edf0f6 !important; border-color:#555d6b !important; }
        input::placeholder, textarea::placeholder { color:#a4abba !important; }
        [data-testid="stMetric"] { background:#22252d !important; color:#edf0f6 !important; border-color:#373b46 !important; }
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3, label, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color:#edf0f6 !important; }
        .dl-data-table, .dl-data-table th, .dl-data-table td { color:#edf0f6; background:#22252d; }
        .dl-data-table th { background:#2c303a !important; }
        .dl-msg.bot { background:#2c303a !important; color:#edf0f6 !important; }
        </style>
        """, unsafe_allow_html=True)

    if dataframe is not None:
        dataset_name = str(table_name or "Uploaded data")
        st.session_state.dashboard_datasets[dataset_name] = dataframe.copy()
        if not st.session_state.dashboard_charts and not st.session_state.dashboard_initialized:
            st.session_state.dashboard_charts = _default_dashboard_charts(dataframe, dataset_name)
            st.session_state.dashboard_initialized = True
    datasets = st.session_state.dashboard_datasets
    numeric = dataframe.select_dtypes(include="number").columns.tolist() if dataframe is not None else []
    categories = [column for column in dataframe.columns if column not in numeric] if dataframe is not None else []
    category_options = categories or (dataframe.columns.tolist() if dataframe is not None else [])
    active_category = st.session_state.get("dl_category", category_options[0] if category_options else None)
    if active_category not in category_options and category_options:
        active_category = category_options[0]
    active_metric = st.session_state.get("dl_metric", numeric[0] if numeric else "Rows")
    if active_metric not in ["Rows"] + numeric:
        active_metric = numeric[0] if numeric else "Rows"

    if st.session_state.report_selection_action and dataframe is not None:
        all_rows = set(range(len(dataframe)))
        current = set(st.session_state.report_selected_rows)
        action = st.session_state.report_selection_action
        st.session_state.report_selected_rows = sorted(all_rows if action == "all" else set() if action == "none" else all_rows - current)
        st.session_state.report_select_all = action == "all"
        st.session_state.report_selection_action = None

    report_page = st.session_state.report_page
    page_count = {"Overview": 1, "Data table": 2, "Dashboard": 3}.get(report_page, 1)
    if dataframe is None:
        st.info("Load a CSV or Excel file from the left, or choose **Sample data** in Home to start.")
    show_fields, show_right = st.session_state.report_show_fields, st.session_state.report_show_right
    weights = ([0.95] if show_fields else []) + [3.0] + ([1.2] if show_right else [])
    columns = st.columns(weights, gap="small")
    col_idx = 0
    fields_col = columns[col_idx] if show_fields else None
    col_idx += 1 if show_fields else 0
    canvas_col = columns[col_idx]
    col_idx += 1
    right_col = columns[col_idx] if show_right else None
    filtered = dataframe.copy() if dataframe is not None else None

    if show_right:
        with right_col:
            right_tab = st.radio("Right pane", ["Visualize", "Filters", "Assistant"], key="report_right_tab", label_visibility="collapsed")
            if dataframe is None:
                st.caption("Load a dataset to configure visuals, filters, and chat.")
            elif right_tab == "Visualize":
                if report_page == "Dashboard":
                    st.caption("Edit each chart inside its tile.")
                else:
                    st.markdown("#### Visualize")
                    st.radio("Chart type", ["Column chart", "Horizontal chart", "Pie chart"], key="dl_chart_type")
                    st.selectbox("Axis", category_options, index=category_options.index(active_category), key="dl_category")
                    st.selectbox("Measure", ["Rows"] + numeric, index=(["Rows"] + numeric).index(active_metric), key="dl_metric")
                    st.color_picker("Chart color", key="overview_chart_color")
            elif right_tab == "Filters":
                st.markdown("#### Filters on this page")
                filter_column = st.selectbox("Filter field", ["All fields"] + dataframe.columns.tolist(), key="dashboard_filter_column")
                if filter_column != "All fields":
                    values = sorted(dataframe[filter_column].dropna().astype(str).unique().tolist())
                    st.multiselect("Keep values", values, key="dashboard_filter_values")
                if st.button("Clear filters", use_container_width=True, key="designer_clear_filters"):
                    st.session_state.dashboard_filter_column = "All fields"
                    st.session_state.dashboard_filter_values = []
                    st.rerun()
            else:
                _render_report_chat(filtered, active_category, active_metric, api_health)

    filter_column = st.session_state.get("dashboard_filter_column", "All fields")
    filter_values = st.session_state.get("dashboard_filter_values", [])
    if dataframe is not None and filter_column in dataframe.columns and filter_values:
        filtered = dataframe[dataframe[filter_column].astype(str).isin(filter_values)].copy()
    elif dataframe is not None:
        filtered = dataframe.copy()

    if show_fields:
        with fields_col:
            st.markdown("#### Fields")
            if dataframe is None:
                st.caption("Fields appear here when you load data.")
            else:
                st.caption(f"▾ {html.escape(str(table_name or 'Data'))}")
                st.markdown("**Dimensions**")
                for field in categories:
                    st.markdown(f"▫ {html.escape(str(field))} · {html.escape(str(dataframe[field].dtype))}")
                st.markdown("**Measures**")
                for field in numeric:
                    st.markdown(f"∑ {html.escape(str(field))} · {html.escape(str(dataframe[field].dtype))}")

    with canvas_col:
        st.markdown({"Overview": "### Overview", "Data table": "### Data table", "Dashboard": "### Dashboard builder"}.get(report_page, "### Overview"))
        if dataframe is None:
            st.markdown('<div class="dl-card"><b>Your report canvas</b><br><span class="dl-muted">Load a dataset to see KPIs, visuals, and the editable dashboard page.</span></div>', unsafe_allow_html=True)
        elif report_page == "Overview":
            kpis = st.columns(4, gap="small")
            kpis[0].metric("Rows", f"{len(filtered):,}")
            kpis[1].metric("Fields", f"{len(filtered.columns):,}")
            kpis[2].metric("Blank cells", f"{int(filtered.isna().sum().sum()):,}")
            selected_count = sum(index in set(st.session_state.report_selected_rows) for index in filtered.index)
            kpis[3].metric("Selected rows", f"{selected_count:,}")
            chart_type = st.session_state.get("dl_chart_type", "Column chart")
            axis = st.session_state.get("dl_category", active_category)
            measure = st.session_state.get("dl_metric", active_metric)
            if axis in filtered.columns:
                figure = _dashboard_chart_figure(filtered, chart_type, axis, "" if measure == "Rows" else measure,
                                                 "Count" if measure == "Rows" else "Sum", height=400,
                                                 accent_color=st.session_state.overview_chart_color)
                line = f"{len(filtered):,} filtered rows" if filter_values else f"All {len(filtered):,} rows"
                st.markdown(f"**{html.escape(str(measure))} by {html.escape(str(axis))}** · {line}")
                if figure is not None:
                    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
                    st.download_button("Export chart", figure.to_html(full_html=True, include_plotlyjs="cdn"), "volara_overview_chart.html", "text/html", key="overview_chart_export")
                else:
                    st.info("No rows match the selected filters.")
        elif report_page == "Data table":
            search = st.text_input("Search this table", placeholder="Type to find a value…", key="report_table_search")
            sort_cols = st.columns([2, 1, 1], gap="small")
            with sort_cols[0]:
                sort_field = st.selectbox("Sort by", ["None"] + dataframe.columns.tolist(), key="report_table_sort")
            with sort_cols[1]:
                sort_direction = st.selectbox("Direction", ["Ascending", "Descending"], key="report_table_direction")
            with sort_cols[2]:
                st.caption(f"{len(filtered):,} filtered rows")
            table_frame = filtered.copy()
            if search.strip():
                mask = table_frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
                table_frame = table_frame[mask]
            if sort_field != "None":
                table_frame = table_frame.sort_values(sort_field, ascending=sort_direction == "Ascending", kind="stable")
            table_frame = table_frame.head(250)
            row_labels = {}
            for index, row in table_frame.iterrows():
                details = " · ".join(f"{column}: {str(row[column])[:36]}" for column in table_frame.columns[:3])
                row_labels[f"{index + 1}: {details}"] = index
            selected_indices = set(st.session_state.report_selected_rows)
            selected_labels = [label for label, index in row_labels.items() if index in selected_indices]
            chosen_labels = st.multiselect("Select rows for this report", list(row_labels), default=selected_labels, key="report_table_selection")
            visible_indices = set(row_labels.values())
            hidden_selection = selected_indices - visible_indices
            st.session_state.report_selected_rows = sorted(hidden_selection | {row_labels[label] for label in chosen_labels})
            st.markdown(f'<div class="dl-muted">Showing up to 250 matching rows · {len(st.session_state.report_selected_rows):,} rows selected</div>', unsafe_allow_html=True)
            preview = table_frame.to_html(index=False, border=0, classes="dl-data-table")
            st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)
        else:
            builder_tools = st.columns(3, gap="small")
            for column, chart_type, label in zip(builder_tools[:3], ["column", "bar", "donut"], ["+ Column chart", "+ Bar chart", "+ Donut chart"]):
                with column:
                    if st.button(label, use_container_width=True, key=f"builder_add_{chart_type}"):
                        add_dashboard_chart(chart_type, str(table_name or next(iter(datasets), "")))
            management_tools = st.columns([1, 3], gap="small")
            with management_tools[0]:
                if st.button("Clear charts", use_container_width=True, key="builder_clear_charts"):
                    st.session_state.dashboard_charts = []
            with management_tools[1]:
                imported_builder_file = st.file_uploader("Import CSV as dataset", type=["csv"], key="builder_dataset_upload")
            if imported_builder_file:
                import_fingerprint = (imported_builder_file.name, len(imported_builder_file.getvalue()))
                if import_fingerprint != st.session_state.builder_upload_fingerprint:
                    imported_dataframe = read_uploaded(imported_builder_file)
                    if imported_dataframe is not None:
                        builder_name = Path(imported_builder_file.name).stem
                        datasets[builder_name] = imported_dataframe
                        st.session_state.builder_upload_fingerprint = import_fingerprint
                        st.success(f"Added {builder_name} · {len(imported_dataframe):,} rows")
            if not datasets:
                st.info("Load data first, then add and edit chart tiles.")
            elif not st.session_state.dashboard_charts:
                st.markdown('<div class="dl-card"><b>No charts yet.</b><br><span class="dl-muted">Add a chart above to start building this page.</span></div>', unsafe_allow_html=True)
            else:
                chart_specs = list(st.session_state.dashboard_charts)
                index = 0
                while index < len(chart_specs):
                    if chart_specs[index].get("span", 6) >= 12:
                        row_specs = [chart_specs[index]]
                        tile_columns = [st.container()]
                        index += 1
                    elif index + 1 < len(chart_specs) and chart_specs[index + 1].get("span", 6) < 12:
                        row_specs = chart_specs[index:index + 2]
                        tile_columns = st.columns(2, gap="small")
                        index += 2
                    else:
                        row_specs = [chart_specs[index]]
                        tile_columns = [st.container()]
                        index += 1
                    for tile_col, spec in zip(tile_columns, row_specs):
                        with tile_col:
                            st.markdown('<div class="dl-card">', unsafe_allow_html=True)
                            _render_builder_chart(spec, datasets, filter_column, filter_values)
                            st.markdown('</div>', unsafe_allow_html=True)

    st.radio("Report pages", ["Overview", "Data table", "Dashboard"], horizontal=True, key="report_page")
    st.markdown(f'<div class="dl-muted" style="border-top:1px solid var(--dl-line);padding-top:8px">Page {page_count} of 3 · {len(dataframe) if dataframe is not None else 0:,} rows · {len(st.session_state.report_selected_rows):,} selected · {html.escape(str(table_name or "No source"))}</div>', unsafe_allow_html=True)


def run_clean(dataframe, api_health):
    if api_health and st.session_state.table_name:
        try:
            response = requests.post(
                f"{API_URL}/api/clean",
                json={
                    "table_name": st.session_state.table_name,
                    "operations": ["trim", "dedupe", "null_fill", "type_fix", "lower_headers"],
                },
                timeout=25,
            )
            response.raise_for_status()
            page = requests.post(
                f"{API_URL}/api/filter-sort",
                json={"table_name": st.session_state.table_name, "page": 1, "page_size": 10000},
                timeout=25,
            )
            page.raise_for_status()
            set_dataset(pd.DataFrame(page.json()["data"]), st.session_state.table_name, st.session_state.source_files, st.session_state.loaded_upload_fingerprint)
            st.toast("Dataset cleaned")
            return
        except requests.RequestException as exc:
            st.error(f"API cleaning failed: {exc}")
            return
    cleaned = dataframe.copy()
    for column in cleaned.select_dtypes(include="object").columns:
        cleaned[column] = cleaned[column].astype(str).str.strip().replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    set_dataset(cleaned, st.session_state.table_name, st.session_state.source_files, st.session_state.loaded_upload_fingerprint)
    st.toast(f"Cleaned locally · {len(cleaned):,} rows")


api_health = api_status()

with st.sidebar:
    st.markdown(
        '<div class="dl-brand"><div class="dl-mark">V</div><div><div class="dl-brand-name">Volara Data Analyst</div><div class="dl-brand-sub">Visual data workspace</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="dl-section">Add data source</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Excel, CSV, SQL, SQLite, JSON, or Parquet",
        type=["csv", "xlsx", "xlsm", "xls", "sql", "db", "sqlite", "json", "parquet"],
        label_visibility="collapsed",
        key="single",
    )
    multi_files = st.file_uploader(
        "Drop 2–3 files to merge",
        type=["csv", "xlsx", "xls", "parquet"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="multi",
    )
    merge_how = st.selectbox("Merge mode", ["concat", "union", "separate"], key="merge_how")
    if st.button("Load sample dataset", use_container_width=True):
        load_sample(api_health)

    st.markdown('<div class="dl-section">Loaded sources</div>', unsafe_allow_html=True)
    if st.session_state.source_files:
        for source in st.session_state.source_files:
            st.markdown(f'<div class="dl-muted">▰ {html.escape(str(source))}</div>', unsafe_allow_html=True)
        st.caption(f"{len(st.session_state.df):,} rows · {len(st.session_state.df.columns)} columns")
        if st.button("Remove dataset", use_container_width=True):
            st.session_state.df = None
            st.session_state.table_name = None
            st.session_state.source_files = []
            st.session_state.loaded_upload_fingerprint = None
            clear_row_selection()
            st.rerun()
    else:
        st.caption("No files loaded")

    st.markdown('<div class="dl-section">Workspace</div>', unsafe_allow_html=True)
    pages = ["Dashboard", "Quick analysis", "Pivot table", "Data Lab", "Ask Volara", "Reports", "Connectors"]
    if st.session_state.page not in pages:
        st.session_state.page = "Dashboard"
    st.radio("Open workspace", pages, key="page", label_visibility="collapsed")

    st.markdown('<div class="dl-section">Connection</div>', unsafe_allow_html=True)
    if api_health:
        status_text = "API connected"
        if api_health.get("ai_enabled"):
            status_text += " · Gemini on"
        else:
            status_text += " · local AI mode"
        st.markdown(f'<div class="dl-muted">● {status_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="dl-muted">● Local mode · API offline</div>', unsafe_allow_html=True)


if multi_files and len(multi_files) >= 2:
    fingerprint = ("multi", tuple((file.name, len(file.getvalue())) for file in multi_files))
    if fingerprint != st.session_state.loaded_upload_fingerprint:
        try:
            api_warning = None
            table_name = "local_dataset"
            parsed = [read_uploaded(file) for file in multi_files]
            if any(frame is None for frame in parsed):
                raise ValueError("Multi-file merge supports CSV, Excel, and Parquet.")
            if api_health:
                try:
                    result = backend_multi_upload(multi_files, merge_how)
                    table_name = result["tables"][0]["table"] if result.get("mode") == "separate" else result["table_name"]
                except requests.RequestException as exc:
                    api_warning = str(exc)
                    table_name = "local_dataset"
            if merge_how == "separate":
                dataframe = parsed[0]
            else:
                dataframe = pd.concat(parsed, ignore_index=True, sort=False)
                if merge_how == "union":
                    dataframe = dataframe.drop_duplicates()
                if not api_health or api_warning:
                    table_name = "local_dataset"
            set_dataset(dataframe, table_name, [file.name for file in multi_files], fingerprint)
            st.toast(f"Loaded {len(multi_files)} files · {len(dataframe):,} rows")
            if api_warning:
                st.warning(f"Loaded the files locally, but the backend rejected them: {api_warning}")
        except Exception as exc:
            st.error(f"Could not load files: {exc}")
elif uploaded_file:
    fingerprint = ("single", uploaded_file.name, len(uploaded_file.getvalue()))
    if fingerprint != st.session_state.loaded_upload_fingerprint:
        try:
            table_name = "local_dataset"
            dataframe = read_uploaded(uploaded_file)
            if api_health:
                try:
                    result = backend_upload(uploaded_file)
                    table_name = result["table_name"]
                    if dataframe is None:
                        dataframe = pd.DataFrame(result.get("preview", []))
                except requests.RequestException as exc:
                    if dataframe is None:
                        raise RuntimeError(f"The backend rejected the file and no local reader is available: {exc}") from exc
                    api_warning = str(exc)
            else:
                api_warning = None
            if dataframe is None:
                raise ValueError("This file type needs the backend. Start both services with RUN_VOLARA_DATA_ANALYST.bat and try again.")
            set_dataset(dataframe, table_name, [uploaded_file.name], fingerprint)
            st.toast(f"Loaded {len(dataframe):,} rows")
            if api_warning:
                st.warning(f"Loaded this file locally, but the backend rejected it: {api_warning}")
        except Exception as exc:
            st.error(f"Could not load file: {exc}")


df = st.session_state.df
numeric_cols = df.select_dtypes(include="number").columns.tolist() if df is not None else []
category_cols = (
    [column for column in df.columns if column not in numeric_cols]
    if df is not None
    else []
)
page = st.session_state.page

header, exports = st.columns([2.3, 1.7], gap="small")
with header:
    st.markdown(
        f'<div class="dl-topbar"><div><div class="dl-title">Volara Data Analyst · {html.escape(page)}</div><div class="dl-subtitle">{html.escape(st.session_state.workspace)} · {html.escape(str(st.session_state.table_name or "No dataset"))} · {len(df) if df is not None else 0:,} rows</div></div></div>',
        unsafe_allow_html=True,
    )
with exports:
    render_downloads(df, st.session_state.table_name, "top")

if page == "Dashboard":
    render_report_designer(df, st.session_state.table_name, api_health)

elif page == "Quick analysis":
    if df is None:
        st.info("Choose a file on the left or load the sample to get a friendly summary.")
    else:
        summary = summarize_dataframe(df)
        st.markdown("### Here is your data, in simple words")
        st.caption("A quick check of how much data you have and what it contains.")
        cards = st.columns(4)
        for col, label, value in zip(
            cards,
            ["Rows", "Columns", "Blank cells", "Repeated rows"],
            [summary["rows"], summary["columns"], summary["missing_cells"], summary["duplicate_rows"]],
        ):
            with col:
                st.metric(label, f"{value:,}")

        if summary["numeric"]:
            measure = st.selectbox("Pick a number to explore", list(summary["numeric"]), key="quick_metric")
            numbers = summary["numeric"][measure]
            st.markdown(f"### What do the numbers say about {html.escape(measure)}?")
            stats = st.columns(4)
            for col, label, value in zip(
                stats,
                ["Total", "Average", "Highest", "Lowest"],
                [numbers["total"], numbers["average"], numbers["highest"], numbers["lowest"]],
            ):
                with col:
                    st.metric(label, f"{value:,.2f}")

        group_fields = [column for column in df.columns if column not in numeric_cols]
        if group_fields:
            group_field = st.selectbox("See which group appears most", group_fields, key="quick_group")
            counts = df[group_field].fillna("Blank").astype(str).value_counts().head(8)
            if not counts.empty:
                group_figure = px.bar(
                    x=counts.values,
                    y=counts.index,
                    orientation="h",
                    labels={"x": "Rows", "y": group_field},
                    title=f"Most common {group_field}",
                    color_discrete_sequence=["#2563eb"],
                )
                group_figure.update_layout(template="plotly_white", height=350, margin=dict(l=12, r=12, t=45, b=12))
                st.plotly_chart(group_figure, use_container_width=True)
        else:
            st.info("This file has no text groups to compare yet. You can still explore its number summaries.")

elif page == "Pivot table":
    if df is None:
        st.info("Load a dataset first. Then choose what to group and compare.")
    else:
        st.markdown("### Build a pivot table")
        st.caption("Choose a row group, an optional column group, and what number to calculate. The table updates automatically.")
        controls = st.columns(4, gap="small")
        with controls[0]:
            row_field = st.selectbox("Group rows by", df.columns.tolist(), key="pivot_rows")
        with controls[1]:
            column_field_label = st.selectbox("Compare across", ["No columns"] + df.columns.tolist(), key="pivot_columns")
        with controls[2]:
            value_field = st.selectbox("Number to summarize", ["Count rows"] + numeric_cols, key="pivot_value")
        with controls[3]:
            aggregation = st.selectbox("Calculate", ["Sum", "Average", "Count", "Lowest", "Highest"], key="pivot_aggregation")

        column_field = None if column_field_label == "No columns" else column_field_label
        value_column = None if value_field == "Count rows" else value_field
        pivot_aggregation = "Count" if value_column is None else aggregation
        try:
            pivot = build_pivot(df, row_field, column_field, value_column, pivot_aggregation)
            if pivot.empty:
                st.info("No matching rows yet. Try a different group.")
            else:
                shown_aggregation = "Count" if value_column is None else aggregation
                st.markdown(f"**Your table:** {shown_aggregation.lower()} of {html.escape(value_field)} by {html.escape(row_field)}")
                shown_pivot = pivot.reset_index()
                table_html = shown_pivot.to_html(index=False, border=0, classes="dl-data-table")
                st.markdown(f'<div class="dl-table-scroll">{table_html}</div>', unsafe_allow_html=True)
                csv = shown_pivot.to_csv(index=False).encode("utf-8")
                st.download_button("Download this pivot table as CSV", csv, "aurlex_pivot.csv", "text/csv")
        except ValueError as exc:
            st.warning(str(exc))

elif page == "Data Lab":
    if df is None:
        st.info("Load a dataset from the left to use Data Lab.")
    else:
        st.markdown('<div class="dl-card-title">Clean, filter, and build a chart</div>', unsafe_allow_html=True)
        tools = st.columns(5, gap="small")
        with tools[0]:
            if st.button("Auto clean", use_container_width=True):
                run_clean(df, api_health)
                st.rerun()
        with tools[1]:
            sort_column = st.selectbox("Sort by", ["None"] + df.columns.tolist(), key="lab_sort")
        with tools[2]:
            sort_direction = st.selectbox("Direction", ["asc", "desc"], key="lab_direction")
        with tools[3]:
            filter_column = st.selectbox("Filter column", ["None"] + df.columns.tolist(), key="lab_filter_column")
        with tools[4]:
            filter_value = st.text_input("Contains", key="lab_filter_value")
        if st.button("Apply sort and filter"):
            filtered = df.copy()
            if filter_column != "None" and filter_value:
                filtered = filtered[filtered[filter_column].astype(str).str.contains(filter_value, case=False, na=False)]
            if sort_column != "None":
                filtered = filtered.sort_values(sort_column, ascending=sort_direction == "asc")
            set_dataset(filtered.reset_index(drop=True), st.session_state.table_name, st.session_state.source_files, st.session_state.loaded_upload_fingerprint)
            st.rerun()

        chart_columns = st.columns(4)
        with chart_columns[0]:
            lab_type = st.selectbox("Chart", ["Bar", "Line", "Area", "Scatter", "Histogram"], key="lab_type")
        with chart_columns[1]:
            lab_x = st.selectbox("X axis", df.columns.tolist(), key="lab_x")
        with chart_columns[2]:
            lab_y = st.selectbox("Y axis", numeric_cols or df.columns.tolist(), key="lab_y")
        with chart_columns[3]:
            lab_color = st.color_picker("Chart color", key="lab_chart_color")
        if lab_type == "Bar":
            lab_fig = px.bar(df, x=lab_x, y=lab_y, template="plotly_white", color_discrete_sequence=[lab_color])
        elif lab_type == "Line":
            lab_fig = px.line(df, x=lab_x, y=lab_y, template="plotly_white", color_discrete_sequence=[lab_color])
        elif lab_type == "Area":
            lab_fig = px.area(df, x=lab_x, y=lab_y, template="plotly_white", color_discrete_sequence=[lab_color])
        elif lab_type == "Scatter":
            lab_fig = px.scatter(df, x=lab_x, y=lab_y, template="plotly_white", color_discrete_sequence=[lab_color])
        else:
            lab_fig = px.histogram(df, x=lab_x, template="plotly_white", color_discrete_sequence=[lab_color])
        st.plotly_chart(lab_fig, use_container_width=True)
        preview = df.head(500).to_html(index=False, border=0, classes="dl-data-table")
        st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)

elif page == "Ask Volara":
    if df is None:
        st.info("Load a dataset from the left to ask questions.")
    else:
        question = st.text_area("Ask in plain English", placeholder="e.g., What are the top five regions by revenue?")
        if st.button("Run query"):
            answer = answer_with_ai(question, df, category_cols[0] if category_cols else None, numeric_cols[0] if numeric_cols else "Rows", api_health)
            st.markdown(f'<div class="dl-card">{html.escape(answer)}</div>', unsafe_allow_html=True)
        if st.session_state.disambig_ctx:
            st.caption(f"Clarification context: {st.session_state.disambig_ctx}")

elif page == "Reports":
    if df is None:
        st.info("Load a dataset from the left to enable exports.")
    else:
        render_downloads(df, st.session_state.table_name, "reports")
        st.markdown("#### Dataset preview")
        preview = df.head(500).to_html(index=False, border=0, classes="dl-data-table")
        st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)

else:
    st.markdown(
        '<div class="dl-card"><div class="dl-card-title">Data connectors</div><p class="dl-muted">The connector view is a placeholder. The current dashboard supports local file uploads and multi-file merges.</p></div>',
        unsafe_allow_html=True,
    )


















