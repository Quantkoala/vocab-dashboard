import streamlit as st
import pandas as pd
import os
import requests
from datetime import date, datetime

# Configuration
SHEET_ID = "1IIjvTR_UAeWFCO8Cp_LqlXoegetyMy4Nxxgk74L03G0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
LOCAL_FILE = "words_local.csv"
TRACK_FILE = "tracking.csv"

# Keyword‑based cluster mapping
cluster_keywords = {
    "Communication Strategies": ["articulate","paraphrase","nuance","elucidate","enunciate","concise","coherent","summarize","verbatim","gist"],
    "Emotional States & Reactions": ["pang","ambivalence","resilience"],
    "Risk & Uncertainty": ["leverage","volatility","contingency"],
    "Cognitive Processes": ["aptitude","inference","metacognition"],
    "Historical & Temporal": ["hiatus","halcyon","epoch"],
    "Social Behavior & Norms": ["hubris","egocentrism","altruism"],
    "Financial & Strategic": ["moat","equity","synergy"]
}

def infer_cluster(word):
    lw = str(word).lower()
    for cl, kws in cluster_keywords.items():
        if lw in kws:
            return cl
    return "Uncategorized"

def fetch_ipa(word):
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        r.raise_for_status()
        data = r.json()
        for entry in data:
            phonetic = entry.get("phonetic") or (entry.get("phonetics") or [{}])[0].get("text")
            if phonetic:
                return phonetic
    except:
        pass
    return ""

def fetch_and_save():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip().str.lower()
    if 'word' not in df or 'translation' not in df:
        st.error("Sheet must contain 'word' and 'translation' columns.")
    if 'cluster' not in df: df['cluster'] = df['word'].apply(infer_cluster)
    if 'ipa' not in df: df['ipa'] = df['word'].apply(fetch_ipa)
    df.to_csv(LOCAL_FILE, index=False)
    return df

@st.cache_data
def load_words():
    if os.path.exists(LOCAL_FILE):
        df = pd.read_csv(LOCAL_FILE)
        df.columns = df.columns.str.strip().str.lower()
        if 'cluster' not in df: df['cluster'] = df['word'].apply(infer_cluster)
        if 'ipa' not in df: df['ipa'] = df['word'].apply(fetch_ipa)
        return df
    return fetch_and_save()

def load_tracking():
    if os.path.exists(TRACK_FILE):
        return pd.read_csv(TRACK_FILE, parse_dates=['date'])
    return pd.DataFrame(columns=['date','time_spent','exercises_completed','score'])

def save_tracking(df):
    df.to_csv(TRACK_FILE, index=False)

def cluster_for_date(df, d):
    if 'cluster' not in df: df['cluster'] = df['word'].apply(infer_cluster)
    clusters = sorted(df['cluster'].dropna().unique())
    return clusters[d.toordinal() % len(clusters)] if clusters else ""

# UI
st.sidebar.title("Vocabulary Dashboard")
if os.path.exists(LOCAL_FILE):
    mtime = datetime.fromtimestamp(os.path.getmtime(LOCAL_FILE))
    count = pd.read_csv(LOCAL_FILE).shape[0]
    st.sidebar.info(f"Local file: {LOCAL_FILE}\nUpdated: {mtime:%Y-%m-%d %H:%M}\nWords: {count}")
else:
    st.sidebar.info("No local file yet.")

if st.sidebar.button("🔄 Refresh Vocabulary"):
    st.cache_data.clear()
    df_refreshed = fetch_and_save()
    st.sidebar.success(f"Fetched {len(df_refreshed)} words")

page = st.sidebar.radio("Go to", ["Daily Exercise","Cluster Summary","Learning Outcome Tracking","Export Enriched Vocabulary"])

data = load_words()
track_df = load_tracking()

if page=="Daily Exercise":
    st.header("📖 Daily Exercise")
    d=st.date_input("Practice date:",date.today())
    cl=cluster_for_date(data,d)
    st.subheader(f"Cluster for {d}: {cl}")
    if cl: st.table(data[data['cluster']==cl][['word','ipa','translation']])
    if 'start' not in st.session_state: st.session_state.start=None
    if st.button("Start Timer"): st.session_state.start=datetime.now()
    if st.button("Stop Timer") and st.session_state.start:
        elapsed=(datetime.now()-st.session_state.start).seconds//60
        st.session_state.time_spent=elapsed; st.success(f"Time: {elapsed} min")
    if 'count' not in st.session_state: st.session_state.count=0
    if st.button("+1 Exercise Completed"): st.session_state.count+=1
    st.write(f"Exercises: {st.session_state.count}")
    score=st.number_input("Today's score (0-20)",0,20,0)
    if st.button("Submit"):
        entry={'date':d,'time_spent':st.session_state.get('time_spent',0),'exercises_completed':st.session_state.count,'score':score}
        track_df=pd.concat([track_df,pd.DataFrame([entry])],ignore_index=True)
        save_tracking(track_df); st.success("Recorded!")
elif page=="Cluster Summary":
    st.header("📋 Cluster Summary")
    sel=st.multiselect("Clusters:",sorted(data['cluster'].unique()),default=sorted(data['cluster'].unique()))
    df_f=data[data['cluster'].isin(sel)]
    q=st.text_input("Search:")
    if q:
        mask=df_f[['word','translation']].apply(lambda c: c.str.contains(q,case=False,na=False))
        df_f=df_f[mask.any(axis=1)]
    for c in sel: st.subheader(c); st.table(df_f[df_f['cluster']==c][['word','ipa','translation']])
    st.download_button("Download CSV",df_f.to_csv(index=False),"vocab_summary.csv","text/csv")
elif page=="Learning Outcome Tracking":
    st.header("📊 Learning Outcome Tracking")
    if track_df.empty: st.info("No records yet.")
    else:
        min_d,max_d=track_df['date'].min().date(),track_df['date'].max().date()
        sd,ed=st.date_input("Select date range:",[min_d,max_d],min_value=min_d,max_value=max_d)
        df_t=track_df[(track_df['date']>=pd.to_datetime(sd))&(track_df['date']<=pd.to_datetime(ed))]
        st.subheader(f"{sd} to {ed}"); st.dataframe(df_t)
        st.line_chart(df_t.set_index('date')[['time_spent','exercises_completed','score']])
        st.bar_chart(df_t.set_index('date')['score'])
        st.download_button("Download Progress",df_t.to_csv(index=False),"vocab_progress.csv","text/csv")
        st.sidebar.download_button("Download All",track_df.to_csv(index=False),"vocab_all_progress.csv","text/csv")
else:
    st.header("📥 Export Enriched Vocabulary")
    if st.button("Generate & Download"):
        df_e=data.copy()
        df_e['ipa']=df_e['word'].apply(fetch_ipa)
        df_e['cluster']=df_e['word'].apply(infer_cluster)
        st.download_button("Download enriched CSV",df_e.to_csv(index=False),"vocab_enriched.csv","text/csv")
