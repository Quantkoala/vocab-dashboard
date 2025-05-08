import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# Configuration
a_sheet_id = "1IIjvTR_UAeWFCO8Cp_LqlXoegetyMy4Nxxgk74L03G0"
csv_url = f"https://docs.google.com/spreadsheets/d/{a_sheet_id}/export?format=csv"
local_file = "words_local.csv"
track_file = "tracking.csv"

# Fetch sheet and persist locally
def fetch_and_save():
    try:
        df = pd.read_csv(csv_url)
        df.columns = [c.strip() for c in df.columns]
        df.to_csv(local_file, index=False)
        return df
    except Exception as e:
        st.error(f"Error fetching sheet: {e}")
        return pd.DataFrame(columns=['word','ipa','translation','cluster'])

@st.cache_data(show_spinner=False)
def load_words():
    # load from local if exists, else fetch
    if os.path.exists(local_file):
        return pd.read_csv(local_file)
    return fetch_and_save()

# Tracking persistence
def load_tracking():
    if os.path.exists(track_file):
        return pd.read_csv(track_file, parse_dates=['date'])
    return pd.DataFrame(columns=['date','time_spent','exercises_completed','score'])

def save_tracking(df):
    df.to_csv(track_file, index=False)

# Determine cluster by date
def cluster_for_date(df, target_date):
    clusters = sorted(df['cluster'].dropna().unique())
    if not clusters:
        return ""
    return clusters[target_date.toordinal() % len(clusters)]

# --- UI ---
# Sidebar metadata
st.sidebar.title("Vocabulary Dashboard")
# Show local file info
def show_local_info():
    if os.path.exists(local_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(local_file))
        count = pd.read_csv(local_file).shape[0]
        st.sidebar.info(f"Using local file:\n{local_file}\nUpdated: {mtime:%Y-%m-%d %H:%M}\nWords: {count}")
    else:
        st.sidebar.info("No local file loaded yet.")
show_local_info()

# Refresh button
if st.sidebar.button("🔄 Refresh Vocabulary from Sheet"):
    st.cache_data.clear()
    df = fetch_and_save()
    st.sidebar.success(f"Fetched {len(df)} words and saved to {local_file}")
    show_local_info()

# Navigation
page = st.sidebar.radio("Go to", ["Daily Exercise", "Cluster Summary", "Learning Outcome Tracking"])

data = load_words()
track_df = load_tracking()

# --- Pages ---
if page == "Daily Exercise":
    st.header("📖 Daily Exercise")
    selected_date = st.date_input("Practice date:", value=date.today())
    cl = cluster_for_date(data, selected_date)
    st.subheader(f"Cluster for {selected_date}: {cl}")
    if cl:
        st.table(data.loc[data['cluster']==cl, ['word','ipa','translation']])
    else:
        st.info("No cluster data available.")

    # Timer
    if 'start' not in st.session_state:
        st.session_state.start = None
    if st.button("Start Timer"):
        st.session_state.start = datetime.now()
    if st.button("Stop Timer") and st.session_state.start:
        elapsed = (datetime.now() - st.session_state.start).seconds // 60
        st.session_state.time_spent = elapsed
        st.success(f"Time: {elapsed} min")

    # Exercise count
    if 'count' not in st.session_state:
        st.session_state.count = 0
    if st.button("+1 Exercise Completed"):
        st.session_state.count += 1
    st.write(f"Exercises: {st.session_state.count}")

    # Score
    score = st.number_input("Today's score (0-20)", min_value=0, max_value=20, value=0)
    if st.button("Submit"): 
        entry = {'date': selected_date, 'time_spent': st.session_state.get('time_spent',0),
                 'exercises_completed': st.session_state.count, 'score': score}
        track_df = pd.concat([track_df, pd.DataFrame([entry])], ignore_index=True)
        save_tracking(track_df)
        st.success("Recorded!")

elif page == "Cluster Summary":
    st.header("📋 Cluster Summary")
    clusters = sorted(data['cluster'].dropna().unique())
    sel = st.multiselect("Clusters:", clusters, default=clusters)
    df_f = data[data['cluster'].isin(sel)]
    q = st.text_input("Search:")
    if q:
        mask = df_f[['word','translation']].apply(lambda c: c.str.contains(q, case=False, na=False))
        df_f = df_f[mask.any(axis=1)]
    for c in sel:
        st.subheader(c)
        st.table(df_f.loc[df_f['cluster']==c, ['word','ipa','translation']])
    st.download_button("Download CSV", df_f.to_csv(index=False), "vocab.csv", "text/csv")

else:
    st.header("📊 Learning Outcome Tracking")
    if track_df.empty:
        st.info("No records yet.")
    else:
        min_d = track_df['date'].min().date(); max_d = track_df['date'].max().date()
        sd, ed = st.date_input("Range:", [min_d, max_d], min_value=min_d, max_value=max_d)
        m = (track_df['date']>=pd.to_datetime(sd)) & (track_df['date']<=pd.to_datetime(ed))
        df_t = track_df.loc[m]
        st.subheader(f"{sd} to {ed}")
        st.dataframe(df_t)
        st.line_chart(df_t.set_index('date')[['time_spent','exercises_completed','score']])
        st.bar_chart(df_t.set_index('date')['score'])
        st.download_button("Download Progress", df_t.to_csv(index=False), "progress.csv", "text/csv")
        st.sidebar.download_button("Download All", track_df.to_csv(index=False), "all_progress.csv", "text/csv")
