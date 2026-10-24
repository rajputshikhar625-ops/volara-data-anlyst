import html
import io
import os
import re
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

st.set_page_config(
    page_title="Aurlex Insights",
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
    name = file_obj.name.lower()
    content = file_obj.getvalue()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(content))
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(content), encoding="latin1")
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    if name.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(content))
    if name.endswith(".json"):
        return pd.read_json(io.BytesIO(content))
    return None


def clear_row_selection():
    st.session_state.pop("datalens_table_editor", None)
    st.session_state["row_selection_default"] = True


def set_dataset(dataframe, table_name=None, sources=None, fingerprint=None):
    st.session_state.df = dataframe.reset_index(drop=True)
    st.session_state.table_name = table_name or "local_dataset"
    st.session_state.source_files = sources or []
    st.session_state.loaded_upload_fingerprint = fingerprint
    clear_row_selection()


def backend_upload(file_obj):
    files = {"file": (file_obj.name, file_obj.getvalue(), file_obj.type or "application/octet-stream")}
    response = requests.post(f"{API_URL}/api/upload", files=files, timeout=35)
    response.raise_for_status()
    return response.json()


def backend_multi_upload(files, merge_how):
    payload = [("files", (file.name, file.getvalue(), file.type or "application/octet-stream")) for file in files]
    response = requests.post(
        f"{API_URL}/api/upload-multi?merge_how={merge_how}",
        files=payload,
        timeout=45,
    )
    response.raise_for_status()
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


def answer_locally(question, dataframe, category, metric):
    if dataframe is None:
        return "Upload a file or load the sample dataset first."
    lower = question.lower()
    response = f"Your dataset has {len(dataframe):,} rows and {len(dataframe.columns)} columns."
    if metric and metric != "Rows" and metric in dataframe.columns:
        response += f"\n\n{metric} totals {dataframe[metric].sum():,.2f} (average {dataframe[metric].mean():,.2f})."
        if category and category in dataframe.columns:
            summary = (
                dataframe.groupby(category, dropna=False)[metric]
                .sum()
                .sort_values(ascending=False)
                .head(5)
            )
            if "top" in lower or "highest" in lower or "most" in lower:
                response += "\n\nTop groups:\n" + "\n".join(
                    f"• {html.escape(str(label))}: {value:,.2f}"
                    for label, value in summary.items()
                )
    response += "\n\nAdd GEMINI_API_KEY to enable natural-language AI queries."
    return response


def answer_with_ai(question, dataframe, category, metric, api_health):
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
            },
            timeout=45,
        )
        result = response.json()
        if response.ok and result.get("status") == "needs_clarification":
            return "\n".join(result.get("questions", ["Please clarify the query."]))
        if response.ok:
            insight = result.get("insight", "Query complete.")
            sql = result.get("sql_query", "")
            return f"{insight}\n\nSQL: {sql}"
        return result.get("detail", response.text)
    except requests.RequestException as exc:
        return f"Could not reach the analysis API: {exc}"


def render_downloads(dataframe, table_name):
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
    buttons = st.columns(3, gap="small")
    with buttons[0]:
        st.download_button("Export Excel", excel_buffer.getvalue(), "aurlex_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with buttons[1]:
        st.download_button("Export CSV", csv_bytes, "aurlex_data.csv", "text/csv", use_container_width=True)
    with buttons[2]:
        st.download_button("Export SQL", sql_text, "aurlex_query.sql", "text/plain", use_container_width=True)


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
        '<div class="dl-brand"><div class="dl-mark">A</div><div><div class="dl-brand-name">Aurlex Insights</div><div class="dl-brand-sub">Visual data workspace</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="dl-section">Add data source</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Excel, CSV, SQL, SQLite, JSON, or Parquet",
        type=["csv", "xlsx", "xls", "sql", "db", "sqlite", "json", "parquet"],
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
    pages = ["Dashboard", "Data Lab", "Ask Aurlex", "Reports", "Connectors"]
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
            parsed = [read_uploaded(file) for file in multi_files]
            if any(frame is None for frame in parsed):
                raise ValueError("Multi-file merge supports CSV, Excel, and Parquet.")
            if api_health:
                result = backend_multi_upload(multi_files, merge_how)
                if result.get("mode") == "separate":
                    frames = parsed[:1]
                    table_name = result["tables"][0]["table"]
                else:
                    frames = parsed
                    table_name = result["table_name"]
                dataframe = pd.concat(frames, ignore_index=True, sort=False)
                if merge_how == "union":
                    dataframe = dataframe.drop_duplicates()
            elif merge_how == "separate":
                dataframe = parsed[0]
                table_name = "local_dataset"
            else:
                dataframe = pd.concat(parsed, ignore_index=True, sort=False)
                if merge_how == "union":
                    dataframe = dataframe.drop_duplicates()
                table_name = "local_dataset"
            set_dataset(dataframe, table_name, [file.name for file in multi_files], fingerprint)
            st.toast(f"Loaded {len(multi_files)} files · {len(dataframe):,} rows")
        except Exception as exc:
            st.error(f"Could not load files: {exc}")
elif uploaded_file:
    fingerprint = ("single", uploaded_file.name, len(uploaded_file.getvalue()))
    if fingerprint != st.session_state.loaded_upload_fingerprint:
        try:
            table_name = "local_dataset"
            dataframe = read_uploaded(uploaded_file)
            if api_health:
                result = backend_upload(uploaded_file)
                table_name = result["table_name"]
                if dataframe is None:
                    dataframe = pd.DataFrame(result.get("preview", []))
            if dataframe is None:
                raise ValueError("This file type needs the API. Start the app with RUN_AURLEX_INSIGHTS.bat and try again.")
            set_dataset(dataframe, table_name, [uploaded_file.name], fingerprint)
            st.toast(f"Loaded {len(dataframe):,} rows")
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
        f'<div class="dl-topbar"><div><div class="dl-title">Aurlex Insights · {html.escape(page)}</div><div class="dl-subtitle">{html.escape(st.session_state.workspace)} · {html.escape(str(st.session_state.table_name or "No dataset"))} · {len(df) if df is not None else 0:,} rows</div></div></div>',
        unsafe_allow_html=True,
    )
with exports:
    render_downloads(df, st.session_state.table_name)

if page == "Dashboard":
    main_column, chat_column = st.columns([2.55, 1], gap="medium")
    with main_column:
        chart_slot = st.empty()
        if df is None:
            with chart_slot.container():
                st.markdown(
                    '<div class="dl-card"><div class="dl-card-title">Your analysis canvas</div><p class="dl-muted">Upload a file from the left or load the sample sales dataset to start.</p></div>',
                    unsafe_allow_html=True,
                )
            st.info("Supported files include CSV, Excel, SQL/SQLite, JSON, and Parquet.")
        else:
            control_column, table_column = st.columns([0.82, 2.5], gap="small")
            with control_column:
                st.markdown('<div class="dl-section">Chart type</div>', unsafe_allow_html=True)
                chart_type = st.radio(
                    "Chart type",
                    ["Column chart", "Horizontal chart", "Pie chart"],
                    key="dl_chart_type",
                    label_visibility="collapsed",
                )
                category = st.selectbox(
                    "Category",
                    category_cols or df.columns.tolist(),
                    key="dl_category",
                )
                metric_options = ["Rows"] + numeric_cols
                metric = st.selectbox("Metric", metric_options, key="dl_metric")
                if st.button("Auto clean", use_container_width=True):
                    run_clean(df, api_health)
                    st.rerun()

            with table_column:
                st.markdown(
                    f'<div class="dl-muted" style="text-align:right;padding:6px 0">Preview · first {min(len(df), 200):,} rows</div>',
                    unsafe_allow_html=True,
                )
                preview = df.head(200).to_html(index=False, border=0, classes="dl-data-table")
                st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)
                chart_df = df
                chart_scope = f"All {len(df):,} rows"

            chart_df = chart_df if df is not None else None
            if chart_df is None or chart_df.empty:
                figure = None
            else:
                if metric == "Rows":
                    grouped = chart_df[category].value_counts(dropna=False).rename("value").reset_index()
                    grouped.columns = [category, "value"]
                    metric_label = "Rows"
                else:
                    grouped = (
                        chart_df.groupby(category, dropna=False)[metric]
                        .sum()
                        .sort_values(ascending=False)
                        .reset_index(name="value")
                    )
                    metric_label = metric
                if chart_type == "Pie chart":
                    figure = px.pie(grouped, names=category, values="value", hole=0.18)
                elif chart_type == "Horizontal chart":
                    figure = px.bar(grouped.sort_values("value"), x="value", y=category, orientation="h", color_discrete_sequence=["#16a34a"])
                else:
                    figure = px.bar(grouped, x=category, y="value", color_discrete_sequence=["#2563eb"])
                figure.update_layout(
                    template="plotly_white",
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font_color="#1f2430",
                    height=400,
                    margin=dict(l=12, r=12, t=20, b=18),
                    showlegend=(chart_type == "Pie chart"),
                    xaxis_title=None if chart_type == "Horizontal chart" else metric_label,
                    yaxis_title=category if chart_type == "Horizontal chart" else None,
                )
                figure.update_xaxes(showgrid=True, gridcolor="#e3e6ec", zeroline=False)
                figure.update_yaxes(showgrid=False, zeroline=False)
            with chart_slot.container():
                chart_title = f"{metric if metric != 'Rows' else 'Rows'} by {category}"
                chart_meta = chart_scope if chart_df is not None else "No rows selected"
                chart_header = st.columns([2.5, 1])
                with chart_header[0]:
                    st.markdown(
                        f'<div class="dl-card-title">{html.escape(chart_title)}</div><div class="dl-muted">{html.escape(chart_meta)}</div>',
                        unsafe_allow_html=True,
                    )
                with chart_header[1]:
                    if figure is not None:
                        st.download_button(
                            "Export chart",
                            figure.to_html(full_html=True, include_plotlyjs="cdn"),
                            "aurlex_dashboard.html",
                            "text/html",
                            use_container_width=True,
                        )
                if figure is None:
                    st.info("No rows are selected. Select rows in the preview to redraw the chart.")
                else:
                    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with chat_column:
        st.markdown('<div class="dl-chat-head">AI Assistant</div>', unsafe_allow_html=True)
        st.caption("Ask about the current dataset")
        messages_area = st.container()
        with messages_area:
            for message in st.session_state.messages[-12:]:
                role = "user" if message.get("role") == "user" else "bot"
                safe_message = html.escape(str(message.get("content", "")))
                st.markdown(f'<div class="dl-msg {role}">{safe_message}</div>', unsafe_allow_html=True)
        with st.form("datalens_chat_form", clear_on_submit=True):
            question = st.text_input("Ask about your data", placeholder="Ask about your data…", label_visibility="collapsed")
            send = st.form_submit_button("Send", use_container_width=True, type="primary")
        if send:
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.messages.append(
                {"role": "assistant", "content": answer_with_ai(question, df, category if df is not None else None, metric if df is not None else None, api_health)}
            )
            st.rerun()

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

        chart_columns = st.columns(3)
        with chart_columns[0]:
            lab_type = st.selectbox("Chart", ["Bar", "Line", "Area", "Scatter", "Histogram"], key="lab_type")
        with chart_columns[1]:
            lab_x = st.selectbox("X axis", df.columns.tolist(), key="lab_x")
        with chart_columns[2]:
            lab_y = st.selectbox("Y axis", numeric_cols or df.columns.tolist(), key="lab_y")
        if lab_type == "Bar":
            lab_fig = px.bar(df, x=lab_x, y=lab_y, template="plotly_white")
        elif lab_type == "Line":
            lab_fig = px.line(df, x=lab_x, y=lab_y, template="plotly_white")
        elif lab_type == "Area":
            lab_fig = px.area(df, x=lab_x, y=lab_y, template="plotly_white")
        elif lab_type == "Scatter":
            lab_fig = px.scatter(df, x=lab_x, y=lab_y, template="plotly_white")
        else:
            lab_fig = px.histogram(df, x=lab_x, template="plotly_white")
        st.plotly_chart(lab_fig, use_container_width=True)
        preview = df.head(500).to_html(index=False, border=0, classes="dl-data-table")
        st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)

elif page == "Ask Aurlex":
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
        render_downloads(df, st.session_state.table_name)
        st.markdown("#### Dataset preview")
        preview = df.head(500).to_html(index=False, border=0, classes="dl-data-table")
        st.markdown(f'<div class="dl-table-scroll">{preview}</div>', unsafe_allow_html=True)

else:
    st.markdown(
        '<div class="dl-card"><div class="dl-card-title">Data connectors</div><p class="dl-muted">The connector view is a placeholder. The current dashboard supports local file uploads and multi-file merges.</p></div>',
        unsafe_allow_html=True,
    )




