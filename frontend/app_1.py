import streamlit as st
import pandas as pd, plotly.express as px, plotly.graph_objects as go, scipy.stats as stats, requests, io, os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
API_URL=os.getenv('API_URL','http://localhost:8000')
st.set_page_config(page_title='Aurlex Insights', page_icon='◼', layout='wide', initial_sidebar_state='expanded')
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');
:root{--bg:#0A0A0B;--panel:#111113;--panel2:#18181B;--border:#232326;--text:#FAFAFA;--text2:#A1A1AA;--text3:#71717A;--green:#22C55E}
html,body,[class*="css"]{font-family:'Geist',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}.stApp{background:var(--bg)}
section[data-testid="stSidebar"]{background:var(--panel)!important;border-right:1px solid var(--border)!important}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px}
.metric-label{font-size:11px;font-weight:500;letter-spacing:0.5px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.metric-value{font-size:24px;font-weight:600;letter-spacing:-0.6px;color:var(--text)}
.metric-delta{font-size:12px;color:var(--text2);margin-top:6px;font-family:'Geist Mono',monospace}
.kbd{font-family:'Geist Mono';font-size:11px;background:#18181B;border:1px solid #232326;padding:2px 6px;border-radius:4px;color:#A1A1AA}
.stButton>button{background:#FAFAFA!important;color:#0A0A0B!important;border-radius:8px!important;font-weight:500!important;height:36px!important}
div[data-testid="stDataFrame"]{border:1px solid #232326;border-radius:10px;overflow:hidden}
</style>
''', unsafe_allow_html=True)

for k in ['df','table_name','charts','workspace','page']:
    if k not in st.session_state:
        st.session_state[k]=None if k!='charts' else []
if not st.session_state.workspace:
    st.session_state.workspace='Acme Corp'
if not st.session_state.page:
    st.session_state.page='Dashboard'

with st.sidebar:
    st.markdown('<div style="display:flex;align-items:center;gap:10px;padding:8px 4px 18px 4px;border-bottom:1px solid #232326;margin-bottom:16px;"><div style="width:28px;height:28px;background:#FAFAFA;color:#0A0A0B;display:flex;align-items:center;justify-content:center;font-weight:700;border-radius:6px;">A</div><div><div style="font-weight:600;font-size:14px;color:#FAFAFA;">Aurlex Insights</div><div style="font-size:11px;color:#A1A1AA;">Enterprise v2 • Linear+Stripe</div></div></div>', unsafe_allow_html=True)
    st.selectbox('Workspace',['Acme Corp','Personal','University Lab'], key='workspace')
    for name in ['Dashboard','Data Lab','Ask Aurlex','Connectors','Reports']:
        if st.button(name, key=f'nav_{name}', use_container_width=True):
            st.session_state.page=name
            st.rerun()
    try:
        r=requests.get(f'{API_URL}/api/health',timeout=1.5)
        if r.status_code==200:
            h=r.json()
            st.markdown(f"<div class='card' style='padding:10px;font-size:12px;'>API {h['status']} • {h['tables_loaded']} tables • AI {'ON' if h['ai_enabled'] else 'OFF'}</div>", unsafe_allow_html=True)
    except:
        st.markdown("<div class='card' style='padding:10px;font-size:12px;'>Local mode</div>", unsafe_allow_html=True)
    uploaded_file=st.file_uploader('Drop CSV/XLSX/Parquet', type=['csv','xlsx','xls','parquet'], label_visibility='collapsed')

api_health=None
try:
    r=requests.get(f'{API_URL}/api/health',timeout=1)
    if r.status_code==200:
        api_health=r.json()
except:
    pass

if uploaded_file and st.session_state.df is None:
    try:
        if api_health:
            files={'file':(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            res=requests.post(f'{API_URL}/api/upload', files=files, timeout=30)
            if res.status_code==200:
                data=res.json()
                st.session_state.table_name=data['table_name']
                if uploaded_file.name.endswith('.csv'):
                    st.session_state.df=pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
                else:
                    st.session_state.df=pd.read_excel(io.BytesIO(uploaded_file.getvalue()))
        else:
            if uploaded_file.name.endswith('.csv'):
                st.session_state.df=pd.read_csv(uploaded_file)
            else:
                st.session_state.df=pd.read_excel(uploaded_file)
            st.session_state.table_name='local_dataset'
    except Exception as e:
        st.error(str(e))

if st.session_state.df is None:
    st.markdown('<p style="font-size:28px;font-weight:650;color:#FAFAFA;">No dataset yet</p><p style="color:#A1A1AA;">Upload in sidebar. Real UI inspired by Linear.app + Stripe Dashboard.</p>', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown('<div class="card"><div class="metric-label">01 Ingest</div><b>Parquet Cache</b><br><span style="color:#A1A1AA;font-size:13px;">Persistent DuckDB file, not memory. Live Google Sheets connector.</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="metric-label">02 Analyze</div><b>Anomaly Autopsy</b><br><span style="color:#A1A1AA;font-size:13px;">Z-score, boxplot, SUMMARIZE in one query.</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><div class="metric-label">03 Ask</div><b>Text-to-SQL</b><br><span style="color:#A1A1AA;font-size:13px;">Gemini Flash with token-optimized prompt.</span></div>', unsafe_allow_html=True)
    st.stop()

df=st.session_state.df
numeric_cols=df.select_dtypes(include=['number']).columns.tolist()
all_cols=df.columns.tolist()
page=st.session_state.page

if page=='Dashboard':
    st.markdown(f"<p style='font-size:28px;font-weight:650;color:#FAFAFA;'>Dashboard</p><p style='color:#A1A1AA;'>{st.session_state.workspace} • {st.session_state.table_name} • {len(df):,} rows</p>", unsafe_allow_html=True)
    if numeric_cols:
        cols=st.columns(4)
        for i,col in enumerate(numeric_cols[:4]):
            with cols[i]:
                total=df[col].sum(); mean=df[col].mean()
                st.markdown(f"<div class='card'><div class='metric-label'>{col}</div><div class='metric-value'>{total:,.0f}</div><div class='metric-delta'>mean {mean:,.1f}</div></div>", unsafe_allow_html=True)
    left,right=st.columns([2.2,1])
    with left:
        st.markdown('<div class="card"><div class="metric-label">Anomaly Autopsy</div>', unsafe_allow_html=True)
        if numeric_cols:
            pcol=st.selectbox('Metric', numeric_cols, label_visibility='collapsed')
            z=stats.zscore(df[pcol].dropna()); outliers=df.loc[df[pcol].notna()].iloc[(abs(z)>2.5).nonzero()[0]]
            if not outliers.empty:
                st.markdown(f"<div style='color:#EAB308;font-size:13px;margin:8px 0;'>⚠ {len(outliers)} outliers</div>", unsafe_allow_html=True)
                fig=px.box(df,y=pcol,points='outliers',template='plotly_dark'); fig.update_layout(height=240,margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
                st.dataframe(outliers.head(10),use_container_width=True,height=200)
            else:
                st.markdown(f"<div style='color:#22C55E;font-size:13px;'>✓ No anomalies</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card"><div class="metric-label">Profile</div>', unsafe_allow_html=True)
        prof=pd.DataFrame({'null %':(df.isnull().sum()/len(df)*100).round(1),'type':df.dtypes.astype(str)}); st.dataframe(prof,use_container_width=True,height=320)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="card" style="margin-top:12px;"><div class="metric-label">Sample</div>', unsafe_allow_html=True)
    st.dataframe(df.head(100),use_container_width=True,height=360)
    st.markdown('</div>', unsafe_allow_html=True)

elif page=='Data Lab':
    st.markdown('<p style="font-size:28px;font-weight:650;color:#FAFAFA;">Data Lab</p>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    f1,f2,f3,f4=st.columns(4)
    with f1:
        title=st.text_input('Title','Revenue by Category')
    with f2:
        ctype=st.selectbox('Type',['Bar','Line','Area','Scatter','Histogram','Heatmap'])
    with f3:
        x=st.selectbox('X',all_cols)
    with f4:
        y=st.selectbox('Y',numeric_cols if numeric_cols else all_cols)
    color=st.selectbox('Group',['None']+all_cols)
    if st.button('Add to canvas'):
        st.session_state.charts.append({'title':title,'type':ctype,'x':x,'y':y,'color':None if color=='None' else color}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    for idx,c in enumerate(st.session_state.charts):
        st.markdown(f"<div class='card' style='margin-top:12px;'><div class='metric-label'>{c['type']}</div><b>{c['title']}</b>", unsafe_allow_html=True)
        try:
            colr=c.get('color')
            if c['type']=='Bar':
                fig=px.bar(df,x=c['x'],y=c['y'],color=colr,template='plotly_dark')
            elif c['type']=='Line':
                fig=px.line(df,x=c['x'],y=c['y'],color=colr,markers=True,template='plotly_dark')
            elif c['type']=='Area':
                fig=px.area(df,x=c['x'],y=c['y'],color=colr,template='plotly_dark')
            elif c['type']=='Scatter':
                fig=px.scatter(df,x=c['x'],y=c['y'],color=colr,template='plotly_dark')
            elif c['type']=='Histogram':
                fig=px.histogram(df,x=c['x'],color=colr,template='plotly_dark')
            else:
                corr=df[numeric_cols].corr() if len(numeric_cols)>=2 else pd.DataFrame(); fig=px.imshow(corr,text_auto=True) if not corr.empty else go.Figure()
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        except Exception as e:
            st.error(str(e))
        if st.button('Remove',key=f'rm_{idx}'):
            st.session_state.charts.pop(idx); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif page=='Ask Aurlex':
    st.markdown(f"<p style='font-size:28px;font-weight:650;color:#FAFAFA;'>Ask Aurlex</p><p style='color:#A1A1AA;'>Table {st.session_state.table_name}</p>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    q=st.text_area('Question',placeholder='Top 5 categories?',height=80,label_visibility='collapsed')
    ask=st.button('Run query →')
    st.markdown('</div>', unsafe_allow_html=True)
    if ask and q.strip() and api_health:
        with st.spinner('Gemini writing SQL...'):
            try:
                res=requests.post(f'{API_URL}/api/ai-query',json={'query':q,'table_name':st.session_state.table_name},timeout=45)
                if res.status_code==200:
                    data=res.json()
                    st.code(data['sql_query'],language='sql')
                    rdf=pd.DataFrame(data['data']); st.dataframe(rdf,use_container_width=True,height=350)
                    st.markdown(f"<div style='background:#18181B;border:1px solid #232326;padding:12px;border-radius:8px;color:#A1A1AA;font-size:13px;'><b style='color:#FAFAFA;'>Insight:</b> {data.get('insight','')}</div>", unsafe_allow_html=True)
                else:
                    st.error(res.json().get('detail'))
            except Exception as e:
                st.error(str(e))

elif page=='Connectors':
    st.markdown('<p style="font-size:28px;font-weight:650;color:#FAFAFA;">Connectors</p><p style="color:#A1A1AA;">Live data for institutions</p>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="card"><div class="metric-label">Google Sheets • Live</div>Paste link, syncs hourly. Code at backend/connectors.py</div>', unsafe_allow_html=True)
        st.text_input('Sheet URL',placeholder='https://docs.google.com/...',label_visibility='collapsed')
    with c2:
        st.markdown('<div class="card"><div class="metric-label">Postgres/MySQL/Supabase</div>Use connector_manager.from_postgres(conn_str, query). Slack webhook for anomaly alerts ready.</div>', unsafe_allow_html=True)

else:
    st.markdown('<p style="font-size:28px;font-weight:650;color:#FAFAFA;">Reports</p>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        csv_data=df.to_csv(index=False).encode('utf-8')
        st.download_button('Download CSV',data=csv_data,file_name='aurlex_clean.csv',mime='text/csv',use_container_width=True)
        buf=io.BytesIO()
        with pd.ExcelWriter(buf,engine='openpyxl') as w:
            df.to_excel(w,index=False,sheet_name='Clean')
        st.download_button('Download Excel',data=buf.getvalue(),file_name='aurlex_report.xlsx',use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="metric-label">Institution</div>Scheduled PDF + shareable link + RLS ready in scheduler.py</div>', unsafe_allow_html=True)
