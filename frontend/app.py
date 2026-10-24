import streamlit as st
import pandas as pd, plotly.express as px, plotly.graph_objects as go, scipy.stats as stats, requests, io, os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
API_URL=os.getenv('API_URL','http://localhost:8000')
st.set_page_config(page_title='Aurlex Insights', page_icon='◼', layout='wide', initial_sidebar_state='expanded')
st.markdown("""
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
""", unsafe_allow_html=True)

for k in ['df','table_name','charts','workspace','page','disambig_ctx']:
    if k not in st.session_state:
        st.session_state[k]=None if k!='charts' else [] if k=='charts' else {} if k=='disambig_ctx' else None
if not st.session_state.workspace:
    st.session_state.workspace='Acme Corp'
if not st.session_state.page:
    st.session_state.page='Dashboard'
if st.session_state.charts is None:
    st.session_state.charts=[]
if st.session_state.disambig_ctx is None:
    st.session_state.disambig_ctx={}

with st.sidebar:
    st.markdown('<div style="display:flex;align-items:center;gap:10px;padding:8px 4px 18px 4px;border-bottom:1px solid #232326;margin-bottom:16px;"><div style="width:28px;height:28px;background:#FAFAFA;color:#0A0A0B;display:flex;align-items:center;justify-content:center;font-weight:700;border-radius:6px;">A</div><div><div style="font-weight:600;font-size:14px;color:#FAFAFA;">Aurlex Insights</div><div style="font-size:11px;color:#A1A1AA;">v2.1 • Multi + Clean + Ask</div></div></div>', unsafe_allow_html=True)
    st.selectbox('Workspace',['Acme Corp','Personal','University Lab'], key='workspace')
    for name in ['Dashboard','Data Lab','Ask Aurlex','Connectors','Reports']:
        if st.button(name, key=f'nav_{name}', use_container_width=True):
            st.session_state.page=name
            st.rerun()
    try:
        r=requests.get(f'{API_URL}/api/health',timeout=1.5)
        if r.status_code==200:
            h=r.json()
            st.markdown(f"<div class='card' style='padding:10px;font-size:12px;'>API {h['status']} • {h['tables_loaded']} tables • AI {'ON' if h['ai_enabled'] else 'OFF'}<br><span style='color:#71717A;font-size:11px;'>{h['version']}</span></div>", unsafe_allow_html=True)
    except:
        st.markdown("<div class='card' style='padding:10px;font-size:12px;'>Local mode</div>", unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:10px;letter-spacing:0.8px;color:#71717A;text-transform:uppercase;margin-bottom:6px;">Single file</div>', unsafe_allow_html=True)
    uploaded_file=st.file_uploader('Drop CSV/XLSX/SQL', type=['csv','xlsx','xls','parquet','sql','db','sqlite','json'], label_visibility='collapsed', key='single')
    st.markdown('<div style="font-size:10px;letter-spacing:0.8px;color:#71717A;text-transform:uppercase;margin:12px 0 6px 0;">Multi-file (2-3 Excel/SQL)</div>', unsafe_allow_html=True)
    multi_files=st.file_uploader('Drop 2-3 to merge', type=['csv','xlsx','xls','parquet'], accept_multiple_files=True, key='multi', label_visibility='collapsed')
    merge_how=st.selectbox('Merge', ['concat','union','separate'], label_visibility='collapsed')

api_health=None
try:
    r=requests.get(f'{API_URL}/api/health',timeout=1)
    if r.status_code==200:
        api_health=r.json()
except:
    pass

def load_from_api_upload(file_obj):
    files={'file':(file_obj.name, file_obj.getvalue(), file_obj.type)}
    res=requests.post(f'{API_URL}/api/upload', files=files, timeout=30)
    if res.status_code==200:
        data=res.json()
        st.session_state.table_name=data['table_name']
        # load locally for UI
        try:
            if file_obj.name.endswith('.csv'):
                st.session_state.df=pd.read_csv(io.BytesIO(file_obj.getvalue()))
            elif file_obj.name.endswith(('.xls','.xlsx')):
                st.session_state.df=pd.read_excel(io.BytesIO(file_obj.getvalue()))
            else:
                st.session_state.df=pd.DataFrame(data['preview'])
        except:
            st.session_state.df=pd.DataFrame(data['preview'])
        st.toast(f"Loaded {data['rows']} rows • Clean report: {data.get('clean_report')}")
    else:
        st.error(res.text)

if multi_files and len(multi_files)>=2 and st.session_state.df is None:
    try:
        if api_health:
            files=[('files',(f.name, f.getvalue(), f.type)) for f in multi_files]
            res=requests.post(f'{API_URL}/api/upload-multi?merge_how={merge_how}', files=files, timeout=45)
            if res.status_code==200:
                data=res.json()
                if data['mode'] in ['concat','union']:
                    st.session_state.table_name=data['table_name']
                    st.session_state.df=pd.DataFrame(data['preview'])
                    # fetch full via filter endpoint? keep preview for now, but load full via API
                    try:
                        full=requests.post(f'{API_URL}/api/filter-sort', json={'table_name':data['table_name'],'page':1,'page_size':1000}, timeout=20)
                        if full.status_code==200:
                            st.session_state.df=pd.DataFrame(full.json()['data'])
                    except:
                        pass
                    st.toast(f"Merged {len(multi_files)} files → {data['rows']} rows")
                else:
                    st.success(f"Created {len(data['tables'])} separate tables: {data['tables']}")
                    # load first
                    first=data['tables'][0]
                    st.session_state.table_name=first['table']
                    # fetch
                    full=requests.post(f'{API_URL}/api/filter-sort', json={'table_name':first['table'],'page':1,'page_size':1000})
                    if full.status_code==200:
                        st.session_state.df=pd.DataFrame(full.json()['data'])
            else:
                st.error(res.text)
    except Exception as e:
        st.error(str(e))
elif uploaded_file and st.session_state.df is None:
    try:
        if api_health:
            load_from_api_upload(uploaded_file)
        else:
            if uploaded_file.name.endswith('.csv'):
                st.session_state.df=pd.read_csv(uploaded_file)
            else:
                st.session_state.df=pd.read_excel(uploaded_file)
            st.session_state.table_name='local_dataset'
    except Exception as e:
        st.error(str(e))

if st.session_state.df is None:
    st.markdown('<p style="font-size:28px;font-weight:650;color:#FAFAFA;">No dataset yet</p><p style="color:#A1A1AA;">Upload 1 file or 2-3 files to merge. Supports CSV, Excel, SQL dump, SQLite.</p>', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown('<div class="card"><div class="metric-label">Multi-upload</div><b>2-3 Excel/SQL</b><br><span style="color:#A1A1AA;font-size:13px;">Concat rows or union deduped. Separate tables option.</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="metric-label">Auto Clean</div><b>Trim + Dedupe + Type Fix</b><br><span style="color:#A1A1AA;font-size:13px;">One-click cleaning, report shown.</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><div class="metric-label">Ask with Clarify</div><b>Rahul in HR vs Tech</b><br><span style="color:#A1A1AA;font-size:13px;">AI detects ambiguity and asks: which Rahul?</span></div>', unsafe_allow_html=True)
    st.stop()

df=st.session_state.df
numeric_cols=df.select_dtypes(include=['number']).columns.tolist()
all_cols=df.columns.tolist()
page=st.session_state.page

# Top bar with cleaning, filtering, sorting controls (for all pages)
st.markdown(f"<p style='font-size:28px;font-weight:650;color:#FAFAFA;margin-bottom:0;'>{page}</p><p style='color:#A1A1AA;font-size:13px;'>{st.session_state.workspace} • {st.session_state.table_name} • {len(df):,} rows • {len(df.columns)} cols</p>", unsafe_allow_html=True)

# Cleaning & Filter bar (always visible)
with st.container():
    st.markdown('<div class="card" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end;">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns([1,1,1,1,1])
    with c1:
        if st.button('🧹 Auto Clean', use_container_width=True):
            if api_health:
                try:
                    res=requests.post(f'{API_URL}/api/clean', json={'table_name':st.session_state.table_name,'operations':['trim','dedupe','null_fill','type_fix','lower_headers']}, timeout=20)
                    if res.status_code==200:
                        data=res.json()
                        st.toast(f"Cleaned: {data['report']['details']}")
                        # reload
                        full=requests.post(f'{API_URL}/api/filter-sort', json={'table_name':st.session_state.table_name,'page':1,'page_size':1000})
                        if full.status_code==200:
                            st.session_state.df=pd.DataFrame(full.json()['data'])
                            st.rerun()
                except Exception as e:
                    st.error(str(e))
            else:
                # local clean
                df_clean=df.copy()
                for col in df_clean.select_dtypes(include=['object']).columns:
                    df_clean[col]=df_clean[col].astype(str).str.strip()
                df_clean=df_clean.drop_duplicates()
                st.session_state.df=df_clean
                st.toast(f"Locally cleaned → {len(df_clean)} rows")
                st.rerun()
    with c2:
        sort_col=st.selectbox('Sort by', ['None']+all_cols, key='sort_col')
    with c3:
        sort_dir=st.selectbox('Dir', ['asc','desc'], key='sort_dir')
    with c4:
        filter_col=st.selectbox('Filter col', ['None']+all_cols, key='filter_col')
    with c5:
        filter_val=st.text_input('Filter value contains', key='filter_val')
    
    if sort_col!='None' or (filter_col!='None' and filter_val):
        if st.button('Apply Sort/Filter'):
            if api_health:
                payload={'table_name':st.session_state.table_name,'page':1,'page_size':1000}
                if sort_col!='None':
                    payload['sort_by']=sort_col
                    payload['sort_dir']=sort_dir
                if filter_col!='None' and filter_val:
                    payload['filters']=[{'column':filter_col,'op':'contains','value':filter_val}]
                try:
                    res=requests.post(f'{API_URL}/api/filter-sort', json=payload, timeout=20)
                    if res.status_code==200:
                        data=res.json()
                        st.session_state.df=pd.DataFrame(data['data'])
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
            else:
                # local filter/sort
                dff=df
                if filter_col!='None' and filter_val:
                    dff=dff[dff[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]
                if sort_col!='None':
                    dff=dff.sort_values(by=sort_col, ascending=(sort_dir=='asc'))
                st.session_state.df=dff
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

if page=='Dashboard':
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
            pcol=st.selectbox('Metric', numeric_cols, label_visibility='collapsed', key='anom')
            z=stats.zscore(df[pcol].dropna()); outliers=df.loc[df[pcol].notna()].iloc[(abs(z)>2.5).nonzero()[0]]
            if not outliers.empty:
                st.markdown(f"<div style='color:#EAB308;font-size:13px;margin:8px 0;'>⚠ {len(outliers)} outliers</div>", unsafe_allow_html=True)
                fig=px.box(df,y=pcol,points='outliers',template='plotly_dark'); fig.update_layout(height=240,margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
                st.dataframe(outliers.head(10),use_container_width=True,height=200)
            else:
                st.markdown("<div style='color:#22C55E;font-size:13px;'>✓ No anomalies</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card"><div class="metric-label">Profile</div>', unsafe_allow_html=True)
        prof=pd.DataFrame({'null %':(df.isnull().sum()/len(df)*100).round(1),'type':df.dtypes.astype(str)}); st.dataframe(prof,use_container_width=True,height=320)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="card" style="margin-top:12px;"><div class="metric-label">Sample</div>', unsafe_allow_html=True)
    st.dataframe(df.head(200),use_container_width=True,height=400)
    st.markdown('</div>', unsafe_allow_html=True)

elif page=='Data Lab':
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
    st.markdown('<div class="card">', unsafe_allow_html=True)
    q=st.text_area('Question',placeholder="e.g., Rahul's salary? (if Rahul in HR and Tech, it will ask which) • Top 5 depts?",height=90,label_visibility='collapsed')
    # Show disambiguation context if any
    if st.session_state.disambig_ctx:
        st.markdown(f"<div style='font-size:12px;color:#A1A1AA;'>Context: {st.session_state.disambig_ctx} <button style='font-size:11px;'>clear</button></div>", unsafe_allow_html=True)
        if st.button('Clear context'):
            st.session_state.disambig_ctx={}
            st.rerun()
    ask=st.button('Run query →')
    st.markdown('</div>', unsafe_allow_html=True)
    if ask and q.strip():
        if api_health:
            with st.spinner('Checking ambiguity + writing SQL...'):
                try:
                    payload={'query':q,'table_name':st.session_state.table_name,'disambiguation_context':st.session_state.disambig_ctx}
                    res=requests.post(f'{API_URL}/api/ai-query',json=payload,timeout=45)
                    if res.status_code==200:
                        data=res.json()
                        if data.get('status')=='needs_clarification':
                            st.markdown('<div class="card" style="margin-top:12px;border:1px solid #EAB308;"><div class="metric-label" style="color:#EAB308;">Needs clarification</div>', unsafe_allow_html=True)
                            for ques in data.get('questions',[]):
                                st.markdown(f"<div style='font-size:14px;margin:8px 0;'>❓ {ques}</div>", unsafe_allow_html=True)
                            # Show options as buttons
                            opts=data.get('options',{})
                            for key, opt in opts.items():
                                st.markdown(f"<div style='font-size:12px;color:#A1A1AA;margin-top:8px;'>{key}</div>", unsafe_allow_html=True)
                                if 'departments' in opt:
                                    for dept in opt['departments']:
                                        if st.button(f"Select {dept} for {key}", key=f"sel_{key}_{dept}"):
                                            st.session_state.disambig_ctx[opt.get('dept_col','department')]=str(dept)
                                            if 'name_value' in opt:
                                                st.session_state.disambig_ctx[opt.get('name_col','name')]=str(opt['name_value'])
                                            st.toast(f"Selected {dept}, now rerun query")
                                            st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.code(data['sql_query'],language='sql')
                            rdf=pd.DataFrame(data['data']); st.dataframe(rdf,use_container_width=True,height=350)
                            st.markdown(f"<div style='background:#18181B;border:1px solid #232326;padding:12px;border-radius:8px;color:#A1A1AA;font-size:13px;'><b style='color:#FAFAFA;'>Insight:</b> {data.get('insight','')}</div>", unsafe_allow_html=True)
                    else:
                        st.error(res.text)
                except Exception as e:
                    st.error(str(e))
        else:
            st.write(df.describe(include='all').T)

elif page=='Connectors':
    st.markdown('<div class="card"><div class="metric-label">Google Sheets • Live</div>Paste link, syncs hourly. Code at backend/connectors.py</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    csv_data=df.to_csv(index=False).encode('utf-8')
    st.download_button('Download CSV',data=csv_data,file_name='aurlex_clean.csv',mime='text/csv',use_container_width=True)
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine='openpyxl') as w:
        df.to_excel(w,index=False,sheet_name='Clean')
    st.download_button('Download Excel',data=buf.getvalue(),file_name='aurlex_report.xlsx',use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
