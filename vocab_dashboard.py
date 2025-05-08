import streamlit as st
import pandas as pd
import os
import requests
from datetime import date, datetime

# Configuration: published CSV link for enriched word list
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNbtoid2HrjpXgDu_Wb36swU0Pd1zMM7jr2igAV8z3QCp3pujWbiWN4IbDLgqMCA/pub?gid=863936811&single=true&output=csv"
LOCAL_FILE = "words_local.csv"
TRACK_FILE = "tracking.csv"

# Cluster keywords mapping
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

# Load or refresh word list with caching (no IPA fetch)
@st.cache_data
def load_words():
    df = pd.read_csv(CSV_URL)
    orig = df.columns.tolist()
    df.columns = df.columns.str.strip().str.lower()
    # Map positional headers if needed
    if 'word' not in df.columns and len(df.columns) >= 1:
        df.rename(columns={df.columns[0]: 'word'}, inplace=True)
    if 'translation' not in df.columns and len(df.columns) >= 3:
        df.rename(columns={df.columns[2]: 'translation'}, inplace=True)
    if 'word' not in df.columns or 'translation' not in df.columns:
        st.error(f"Sheet must contain 'word' and 'translation'. Found: {orig}")
        return pd.DataFrame(columns=['word','ipa','translation','cluster'])
    # Infer cluster, leave IPA blank for speed
    df['cluster'] = df.get('cluster', df['word'].apply(infer_cluster))
    df['ipa'] = ''  # skip IPA fetch on load for performance
    # Cache locally
    df.to_csv(LOCAL_FILE, index=False)
    return df

# Tracking
@st.cache_data
def load_tracking():
    if os.path.exists(TRACK_FILE):
        return pd.read_csv(TRACK_FILE, parse_dates=['date'])
    return pd.DataFrame(columns=['date','time_spent','score'])

def save_tracking(df):
    df.to_csv(TRACK_FILE, index=False)

def cluster_for_date(df, d):
    clusters = sorted(df['cluster'].dropna().unique())
    return clusters[d.toordinal() % len(clusters)] if clusters else ""

# App UI
st.sidebar.title("Vocabulary Dashboard")
if st.sidebar.button("🔄 Refresh Words"):
    load_words()
    st.sidebar.success("Words refreshed")
page = st.sidebar.radio("Go to", ["Daily Practice","Learning Outcome Tracking"])

data = load_words()
track = load_tracking()

if page == "Daily Practice":
    st.header("📝 Daily Practice")
    sel_date = st.date_input("Practice date:", date.today())
    today_cluster = cluster_for_date(data, sel_date)
    st.subheader(f"Today's Cluster: {today_cluster}")
    # Display clusters as tabs
    cluster_list = sorted(data['cluster'].unique())
    tabs = st.tabs(cluster_list)
    for tab, cl in zip(tabs, cluster_list):
        with tab:
            words_cl = data[data['cluster']==cl][['word','ipa','translation']]
            cols = st.columns(3)
            for i, row in words_cl.iterrows():
                col = cols[i % 3]
                col.markdown(f"**{row['word']}**")
                col.markdown(f"/{row['ipa']}/")
                col.markdown(row['translation'])
    # Timer
    if 'start' not in st.session_state: st.session_state.start = None
    if 'time_spent' not in st.session_state: st.session_state.time_spent = 0
    c1, c2 = st.columns(2)
    if c1.button("Start Timer"): st.session_state.start = datetime.now()
    if c2.button("Stop Timer") and st.session_state.start:
        delta = datetime.now() - st.session_state.start
        st.session_state.time_spent = int(delta.total_seconds()//60)
        st.success(f"Time: {st.session_state.time_spent} min")
    # Quiz
    cluster_words = data[data['cluster']==today_cluster].sample(min(5,len(data[data['cluster']==today_cluster])))
    form = st.form("quiz")
    answers = {}
    for idx, row in cluster_words.iterrows():
        answers[idx] = form.text_input(f"Spell the word for '{row['translation']}'", key=f"ans{idx}")
    submitted = form.form_submit_button("Submit Answers")
    if submitted:
        score = sum(1 for idx,row in cluster_words.iterrows() if answers[idx].strip().lower()==row['word'].lower())
        st.write(f"Score: {score}/{len(cluster_words)}")
        track = pd.concat([track, pd.DataFrame([{'date':sel_date,'time_spent':st.session_state.time_spent,'score':score}])], ignore_index=True)
        save_tracking(track)

else:
    st.header("📊 Learning Outcome Tracking")
    if track.empty:
        st.info("No records yet.")
    else:
        st.line_chart(track.set_index('date')[['time_spent','score']])
        st.table(track)
