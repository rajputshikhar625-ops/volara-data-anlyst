import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as stats
import requests
import io
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Aurlex Insights | Enterprise Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Styling ----
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-header { font-size: 2.8rem; font-weight: 800; color: #0F172A; letter-spacing: -1px; }
    .sub-header { font-size: 1.15rem; color: #475569; margin-bottom: 1.5rem; }
    .kpi-card { background: white; border-radius: 12px; padding: 16px; border: 1px solid #E2E8F0; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 8px; font-weight: 600; background: #0F172A; color: white; }
    .stButton>button:hover { background: #1E293B; color: white; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Aurlex Insights Platform</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Autonomous Data Compilation • Dynamic Visualizations • Conversational Analytics • DuckDB + Gemini</p>', unsafe_allow_html=True)

# Session
if 'df' not in st.session_state:
    st.session_state.df = None
if 'table_name' not in st.session_state:
    st.session_state.table_name = None
if 'charts' not in st.session_state:
    st.session_state.charts = []

# Sidebar
st.sidebar.header("📁 Data Management")
st.sidebar.markdown("Upload to local DuckDB engine")
uploaded_file = st.sidebar.file_uploader("CSV / Excel / Parquet", type=["csv", "xlsx", "xls", "parquet"])

api_health = None
try:
    r = requests.get(f"{API_URL}/api/health", timeout=2)
    if r.status_code == 200:
        api_health = r.json()
        st.sidebar.success(f"API: {api_health['status']} | AI: {'ON' if api_health['ai_enabled'] else 'OFF'}")
except:
    st.sidebar.info("API offline - running in standalone Streamlit mode (local analysis)")

if uploaded_file is not None:
    try:
        if api_health:
            # Use FastAPI backend
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            res = requests.post(f"{API_URL}/api/upload", files=files)
            if res.status_code == 200:
                data = res.json()
                st.session_state.table_name = data["table_name"]
                # Fetch preview for local UI
                if uploaded_file.name.endswith('.csv'):
                    st.session_state.df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
                else:
                    st.session_state.df = pd.read_excel(io.BytesIO(uploaded_file.getvalue()))
                st.sidebar.success(f"Loaded to {data['table_name']}: {data['rows']} rows")
            else:
                st.sidebar.error(res.json().get("detail"))
        else:
            # Fallback local load
            if uploaded_file.name.endswith('.csv'):
                st.session_state.df = pd.read_csv(uploaded_file)
            else:
                st.session_state.df = pd.read_excel(uploaded_file)
            st.sidebar.success(f"Loaded {st.session_state.df.shape[0]} rows (local mode)")
            st.session_state.table_name = "local_dataset"
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

if st.session_state.df is not None:
    df = st.session_state.df
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    all_cols = df.columns.tolist()

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Executive Dashboard", "🛠️ Custom Chart Builder", "🤖 AI Data Assistant", "📥 Reports & Exports"])

    with tab1:
        st.subheader("Key Performance Indicators & Anomaly Autopsy")
        if numeric_cols:
            k1, k2, k3, k4 = st.columns(4)
            cols = [k1,k2,k3,k4]
            for i, col in enumerate(numeric_cols[:4]):
                with cols[i]:
                    st.metric(label=f"Total {col}", value=f"{df[col].sum():,.2f}", delta=f"Mean {df[col].mean():,.2f}")

            st.markdown("---")
            c1, c2 = st.columns([2,1])
            with c1:
                primary_col = st.selectbox("Select metric for anomaly scan", numeric_cols, key="anom_col")
                z_scores = stats.zscore(df[primary_col].dropna())
                outliers = df.loc[df[primary_col].notna()].iloc[(abs(z_scores) > 2.5).nonzero()[0]]
                if not outliers.empty:
                    st.warning(f"⚠️ **Anomaly Alert:** {len(outliers)} outlier events in `{primary_col}` (>2.5σ)")
                    st.dataframe(outliers.head(20), use_container_width=True)
                    fig = px.box(df, y=primary_col, points="all", template="plotly_white", title=f"Distribution & Outliers: {primary_col}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success(f"✅ **Data Health Clean:** No significant anomalies in `{primary_col}`")
            with c2:
                st.markdown("#### Data Quality")
                null_pct = (df.isnull().sum() / len(df) * 100).round(1)
                qdf = pd.DataFrame({"null_%": null_pct, "dtype": df.dtypes.astype(str)})
                st.dataframe(qdf, use_container_width=True)
        else:
            st.info("No numeric columns detected for KPI analysis")
        
        st.markdown("---")
        st.dataframe(df.head(100), use_container_width=True, height=350)

    with tab2:
        st.subheader("Dynamic Visual Builder")
        with st.form("chart_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                title = st.text_input("Chart Title", value="Performance Metric Analysis")
            with c2:
                chart_type = st.selectbox("Chart Type", ["Line Chart", "Bar Chart", "Pie Chart", "Scatter Plot", "Area Chart", "Histogram", "Heatmap"])
            with c3:
                x_dim = st.selectbox("X-Axis / Category", all_cols)
            y_dim = st.selectbox("Y-Axis / Metric", numeric_cols if numeric_cols else all_cols)
            color_dim = st.selectbox("Color / Group (optional)", ["None"] + all_cols)
            add_btn = st.form_submit_button("Add Chart to Canvas")
            if add_btn:
                st.session_state.charts.append({"title": title, "type": chart_type, "x": x_dim, "y": y_dim, "color": None if color_dim=="None" else color_dim})

        if st.session_state.charts:
            st.markdown("### Active Dashboard Canvas")
            for idx, c in enumerate(st.session_state.charts):
                st.markdown(f"#### {c['title']}")
                color = c.get("color")
                try:
                    if c['type'] == "Line Chart":
                        fig = px.line(df, x=c['x'], y=c['y'], color=color, markers=True, template="plotly_white")
                    elif c['type'] == "Bar Chart":
                        fig = px.bar(df, x=c['x'], y=c['y'], color=color, template="plotly_white")
                    elif c['type'] == "Pie Chart":
                        fig = px.pie(df, names=c['x'], values=c['y'])
                    elif c['type'] == "Scatter Plot":
                        fig = px.scatter(df, x=c['x'], y=c['y'], color=color, template="plotly_white")
                    elif c['type'] == "Area Chart":
                        fig = px.area(df, x=c['x'], y=c['y'], color=color, template="plotly_white")
                    elif c['type'] == "Histogram":
                        fig = px.histogram(df, x=c['x'], color=color, template="plotly_white")
                    else:
                        corr = df[numeric_cols].corr() if len(numeric_cols)>=2 else pd.DataFrame()
                        fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap") if not corr.empty else go.Figure()
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Chart error: {e}")
                
                if st.button(f"Remove Chart #{idx+1}", key=f"rem_{idx}"):
                    st.session_state.charts.pop(idx)
                    st.rerun()
        else:
            st.info("No charts yet. Use the form above to build your canvas.")

    with tab3:
        st.subheader("Conversational AI Assistant")
        st.markdown(f"**Active Table:** `{st.session_state.table_name}` | **AI Engine:** Gemini 1.5 Flash" if api_health and api_health.get('ai_enabled') else "AI running in heuristic mode (add GEMINI_API_KEY for full autonomy)")
        
        user_prompt = st.text_area("Ask in plain English", placeholder="e.g., What are top 5 regions by total revenue? Show monthly trend of sales? Any correlation between discount and profit?")
        if st.button("Ask AI", type="primary"):
            if not user_prompt.strip():
                st.warning("Enter a question")
            else:
                if api_health and st.session_state.table_name:
                    with st.spinner("Analyzing with Gemini Flash + DuckDB..."):
                        try:
                            payload = {"query": user_prompt, "table_name": st.session_state.table_name}
                            res = requests.post(f"{API_URL}/api/ai-query", json=payload, timeout=60)
                            if res.status_code == 200:
                                data = res.json()
                                st.code(data["sql_query"], language="sql")
                                st.markdown("#### Result")
                                rdf = pd.DataFrame(data["data"])
                                st.dataframe(rdf, use_container_width=True)
                                if len(rdf)>0 and len(rdf.columns)>=2 and pd.api.types.is_numeric_dtype(rdf[rdf.columns[1]]):
                                    try:
                                        fig = px.bar(rdf.head(20), x=rdf.columns[0], y=rdf.columns[1], template="plotly_white")
                                        st.plotly_chart(fig, use_container_width=True)
                                    except:
                                        pass
                                st.markdown("#### 💡 Autonomous Insight")
                                st.info(data.get("insight","No insight"))
                            else:
                                st.error(res.json().get("detail"))
                        except Exception as e:
                            st.error(f"AI query failed: {e}")
                else:
                    # Local heuristic fallback
                    st.info(f"Query received: '{user_prompt}'. Running local pandas analysis...")
                    if numeric_cols:
                        st.write(df[numeric_cols].describe().T)
                    if categorical_cols and numeric_cols:
                        grp = df.groupby(categorical_cols[0])[numeric_cols[0]].sum().sort_values(ascending=False).head(10)
                        st.bar_chart(grp)

    with tab4:
        st.subheader("Export & Report Generation")
        col1, col2 = st.columns(2)
        with col1:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Cleaned Dataset (CSV)", data=csv_data, file_name="aurlex_clean_report.csv", mime="text/csv", use_container_width=True)
            # Excel export
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="CleanData")
                if numeric_cols:
                    df[numeric_cols].describe().to_excel(writer, sheet_name="Summary")
            st.download_button("📊 Download Excel Report", data=buf.getvalue(), file_name="aurlex_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with col2:
            if st.button("📄 Generate PDF Executive Brief", use_container_width=True):
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    pdf_buf = io.BytesIO()
                    c = canvas.Canvas(pdf_buf, pagesize=letter)
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(40, 750, "Aurlex Insights - Executive Brief")
                    c.setFont("Helvetica", 11)
                    c.drawString(40, 730, f"Rows: {len(df)} | Columns: {len(df.columns)} | Table: {st.session_state.table_name}")
                    y=700
                    for col in df.columns[:15]:
                        c.drawString(40, y, f"- {col}: {df[col].dtype} | Nulls: {df[col].isnull().sum()}")
                        y-=15
                        if y<50:
                            c.showPage()
                            y=750
                    c.save()
                    st.download_button("Download PDF", data=pdf_buf.getvalue(), file_name="aurlex_brief.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"PDF error: {e}")

else:
    st.info("👈 Upload a dataset in the sidebar to initialize Aurlex Insights")
    st.markdown("""
    ### How to run locally
    ```bash
    pip install -r requirements.txt
    cp .env.example .env  # add your GEMINI_API_KEY
    uvicorn backend.main:app --reload --port 8000
    # in another terminal
    streamlit run frontend/app.py
    ```
    ### Deploy free
    - **Streamlit Cloud**: Connect repo, set secrets, main file = frontend/app.py
    - **Render / Railway**: Use Dockerfile, expose 8000 + 8501
    - **HuggingFace Spaces**: Streamlit SDK
    """)

