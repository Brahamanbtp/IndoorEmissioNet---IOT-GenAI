# """
# app_streamlit_ollama.py

# Streamlit dashboard: reads ThingSpeak channel, shows live chart, and calls local
# Ollama model (gemma:2b) to summarize the most recent N sensor readings.

# Usage:
#   1) Install dependencies (see requirements.txt)
#   2) Export environment variables (optional) or set in UI:
#       THINGSPEAK_CHANNEL (default: 3083670)
#       THINGSPEAK_READ_KEY (your read API key)
#       OLLAMA_URL (default: http://localhost:11434/api/generate)
#       OLLAMA_MODEL (default: gemma:2b)
#   3) streamlit run app_streamlit_ollama.py
# """

# import os
# import time
# import requests
# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from datetime import datetime, timezone

# # ---------------- Configuration (environment defaults)
# THINGSPEAK_CHANNEL = int(os.getenv("THINGSPEAK_CHANNEL", "3083670"))
# THINGSPEAK_READ_KEY = os.getenv("THINGSPEAK_READ_KEY", "SGF2O4G9P7X6RWAR")
# THINGSPEAK_BASE = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL}/feeds.json"

# OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

# DEFAULT_FETCH = int(os.getenv("DEFAULT_FETCH", "200"))
# DEFAULT_POLL = int(os.getenv("DEFAULT_POLL", "15"))

# # ---------------- Helper functions
# @st.cache_data(ttl=10)
# def fetch_thingspeak(n=200):
#     params = {"api_key": THINGSPEAK_READ_KEY, "results": n}
#     r = requests.get(THINGSPEAK_BASE, params=params, timeout=12)
#     r.raise_for_status()
#     data = r.json()
#     feeds = data.get("feeds", [])
#     if not feeds:
#         return pd.DataFrame()
#     df = pd.DataFrame(feeds)
#     # convert timestamps and numeric fields
#     df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
#     # assume primary metric in field1
#     df['field1'] = pd.to_numeric(df.get('field1'), errors='coerce')
#     # also include field2/3 if you have DHT
#     for f in ('field2','field3','field4','field5'):
#         if f in df.columns:
#             df[f] = pd.to_numeric(df.get(f), errors='coerce')
#     return df.sort_values('created_at')

# def prepare_prompt(df, max_points=50):
#     arr = df['field1'].dropna().tail(max_points).tolist()
#     if not arr:
#         return "No numeric readings available to summarize."
#     last_time = df['created_at'].iloc[-1].astimezone().strftime("%Y-%m-%d %H:%M:%S")
#     # create a concise prompt
#     prompt = (
#         f"You are an air-quality assistant. The last reading time is {last_time} (local time).\n"
#         f"Here are the last {len(arr)} AirQuality readings (oldest to newest):\n"
#         f"{', '.join([str(round(float(x),3)) for x in arr])}\n\n"
#         "Produce a short (max 100 words) human-friendly summary that includes:\n"
#         "- whether air quality is improving, worsening, or stable\n"
#         "- whether there are any spikes or anomalies\n"
#         "- a severity rating (low/medium/high)\n"
#         "- one clear recommended action (one short sentence)\n"
#         "Return just the summary (no JSON)."
#     )
#     return prompt

# def call_ollama(prompt, model=OLLAMA_MODEL, ollama_url=OLLAMA_URL, timeout=30):
#     """
#     Calls local Ollama HTTP endpoint. Expects Ollama JSON response.
#     Payload uses keys: model, prompt, stream=false
#     """
#     payload = {"model": model, "prompt": prompt, "stream": False}
#     try:
#         resp = requests.post(ollama_url, json=payload, timeout=timeout)
#         resp.raise_for_status()
#         j = resp.json()
#         # try common response keys used by Ollama variants
#         if isinstance(j, dict):
#             for key in ("response", "result", "text", "output"):
#                 if key in j and j[key]:
#                     return str(j[key])
#             # sometimes 'choices' is provided (OpenAI-like)
#             if "choices" in j and isinstance(j["choices"], list) and len(j["choices"])>0:
#                 c = j["choices"][0]
#                 if isinstance(c, dict):
#                     for k in ("message","text","output"):
#                         if k in c:
#                             return str(c[k])
#                     # fallback
#                     return str(c)
#             return str(j)
#         return str(j)
#     except Exception as e:
#         return f"[ERROR calling Ollama: {e}]"

# # ---------------- Streamlit UI
# st.set_page_config(page_title="Air Quality Dashboard + Ollama", layout="wide")
# st.title("Air Quality Dashboard — ThingSpeak + Ollama (gemma:2b)")

# # Sidebar controls
# with st.sidebar:
#     st.header("Settings")
#     nf = st.number_input("Fetch last N points", value=DEFAULT_FETCH, min_value=10, max_value=2000, step=10)
#     poll = st.number_input("Auto-refresh interval (s)", value=DEFAULT_POLL, min_value=5, max_value=3600)
#     st.markdown("---")
#     st.subheader("ThingSpeak")
#     st.write(f"Channel: {THINGSPEAK_CHANNEL}")
#     st.text("Field used: field1 (Air Quality)")
#     st.markdown("---")
#     st.subheader("Ollama")
#     ollama_url = st.text_input("Ollama API URL", value=OLLAMA_URL)
#     ollama_model = st.text_input("Ollama model name", value=OLLAMA_MODEL)
#     st.write("Note: Ollama must be running locally and model pulled (e.g., `ollama pull gemma:2b`).")
#     st.markdown("---")
#     if st.button("Refresh now"):
#         st.experimental_memo.clear()
#         st.experimental_rerun()

# # Fetch data
# try:
#     df = fetch_thingspeak(n=nf)
# except Exception as e:
#     st.error(f"Error fetching ThingSpeak data: {e}")
#     st.stop()

# if df.empty:
#     st.warning("No data returned from ThingSpeak. Check channel/read key.")
#     st.stop()

# # Main layout
# col_chart, col_table = st.columns([3,1])

# with col_chart:
#     st.subheader("Live Air Quality (field1)")
#     fig = px.line(df, x='created_at', y='field1', title='Air Quality (field1)', labels={'created_at':'Time','field1':'AirQuality'})
#     fig.update_xaxes(rangeslider_visible=True)
#     st.plotly_chart(fig, use_container_width=True)

# with col_table:
#     st.subheader("Latest")
#     latest_val = df['field1'].iloc[-1]
#     latest_ts = df['created_at'].iloc[-1].astimezone().strftime("%Y-%m-%d %H:%M:%S")
#     st.metric("Latest value", f"{latest_val:.3f}" if pd.notna(latest_val) else "N/A")
#     st.write("Timestamp")
#     st.write(latest_ts)
#     st.write(f"Points: {len(df)}")
#     if 'field2' in df.columns:
#         st.write("field2 example (maybe temp):", df['field2'].dropna().tail(1).iloc[0] if not df['field2'].dropna().empty else "N/A")

# st.subheader("Recent Data (last 200 rows)")
# st.dataframe(df[['created_at','field1']].tail(200).reset_index(drop=True))

# # AI summary panel
# st.markdown("## AI Summary (local Ollama)")
# max_pts = st.slider("Use last how many points for summary?", 5, min(50, max(50,len(df))), value=min(50,len(df)))
# if st.button("Generate AI Summary (Ollama)"):
#     prompt = prepare_prompt(df, max_points=max_pts)
#     st.info("Calling Ollama... this might take a few seconds")
#     with st.spinner("Generating summary via Ollama..."):
#         summary = call_ollama(prompt, model=ollama_model, ollama_url=ollama_url)
#     st.success("AI Summary")
#     st.write(summary)

# # Auto-refresh loop: simple approach for local use
# st.caption(f"Auto-refresh every {poll} seconds. The page will reload to fetch fresh data.")
# time.sleep(poll)
# st.experimental_rerun()




# project.py
"""
Streamlit dashboard: read ThingSpeak channel (field1 = Air Quality),
display live chart and table, and call local Ollama model (gemma:2b)
to generate a human summary of recent readings.

Fixed: safe conversion of pandas Timestamp -> local time (avoids tz_convert TypeError).
"""

import os
import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# ---------------- Config / environment defaults ----------------
THINGSPEAK_CHANNEL = int(os.getenv("THINGSPEAK_CHANNEL", "3083670"))
THINGSPEAK_READ_KEY = os.getenv("THINGSPEAK_READ_KEY", "SGF2O4G9P7X6RWAR")
THINGSPEAK_BASE = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL}/feeds.json"

# Ollama settings (local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

DEFAULT_FETCH = int(os.getenv("DEFAULT_FETCH", "200"))
DEFAULT_POLL = int(os.getenv("DEFAULT_POLL", "15"))

# ---------------- Helper functions ----------------
@st.cache_data(ttl=10)
def fetch_thingspeak(n=200):
    params = {"api_key": THINGSPEAK_READ_KEY, "results": n}
    r = requests.get(THINGSPEAK_BASE, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()
    feeds = data.get("feeds", [])
    if not feeds:
        return pd.DataFrame()
    df = pd.DataFrame(feeds)
    # convert timestamps to pandas Timestamp (keep tz info if present)
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    # parse numeric fields
    df['field1'] = pd.to_numeric(df.get('field1'), errors='coerce')
    for f in ('field2','field3','field4','field5'):
        if f in df.columns:
            df[f] = pd.to_numeric(df.get(f), errors='coerce')
    return df.sort_values('created_at')

def timestamp_to_local_str(ts):
    """
    Safely convert a pandas Timestamp (tz-aware or naive) to a localized string.
    Returns string like '2025-09-21 02:24:27'.
    """
    if pd.isna(ts):
        return "N/A"
    # Ensure we have a python datetime
    py_ts = pd.to_datetime(ts).to_pydatetime()
    try:
        # Convert to local timezone (works for naive and tz-aware datetimes)
        local_dt = py_ts.astimezone()
    except Exception:
        # Fallback: use naive datetime formatting
        local_dt = py_ts
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

def prepare_prompt(df, max_points=50):
    arr = df['field1'].dropna().tail(max_points).tolist()
    if not arr:
        return "No numeric readings available to summarize."
    # safe timestamp string
    last_ts = timestamp_to_local_str(df['created_at'].iloc[-1])
    prompt = (
        f"You are an air-quality assistant. The last reading time is {last_ts} (local time).\n"
        f"Here are the last {len(arr)} AirQuality readings (oldest -> newest):\n"
        f"{', '.join([str(round(float(x),3)) for x in arr])}\n\n"
        "Produce a short (max 100 words) human-friendly summary that includes:\n"
        "- whether air quality is improving, worsening, or stable\n"
        "- whether there are any spikes or anomalies\n"
        "- a severity rating (low/medium/high)\n"
        "- one clear recommended action (one short sentence)\n"
        "Return only the summary (no JSON)."
    )
    return prompt

def call_ollama(prompt, model=OLLAMA_MODEL, ollama_url=OLLAMA_URL, timeout=30):
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        resp = requests.post(ollama_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        j = resp.json()
        # try common response keys
        if isinstance(j, dict):
            for key in ("response", "result", "text", "output"):
                if key in j and j[key]:
                    return str(j[key])
            if "choices" in j and isinstance(j["choices"], list) and len(j["choices"])>0:
                c = j["choices"][0]
                if isinstance(c, dict):
                    for k in ("message","text","output"):
                        if k in c:
                            return str(c[k])
                    return str(c)
            return str(j)
        return str(j)
    except Exception as e:
        return f"[ERROR calling Ollama: {e}]"

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Indoor Air Quality — ThingSpeak + Ollama", layout="wide")
st.title("Indoor Air Quality — Live (ThingSpeak → Ollama)")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    nf = st.number_input("Fetch last N points", value=DEFAULT_FETCH, min_value=10, max_value=2000, step=10)
    poll = st.number_input("Auto-refresh interval (s)", value=DEFAULT_POLL, min_value=5, max_value=3600)
    st.markdown("---")
    st.subheader("ThingSpeak")
    st.write(f"Channel: {THINGSPEAK_CHANNEL}")
    st.text("Field used: field1 (Air Quality)")
    st.markdown("---")
    st.subheader("Ollama")
    ollama_url = st.text_input("Ollama API URL", value=OLLAMA_URL)
    ollama_model = st.text_input("Ollama model name", value=OLLAMA_MODEL)
    st.write("Make sure Ollama is running locally and model pulled (e.g., `ollama pull gemma:2b`).")
    st.markdown("---")
    if st.button("Refresh now"):
        st.experimental_memo.clear()
        st.experimental_rerun()

# Fetch data from ThingSpeak
try:
    df = fetch_thingspeak(n=nf)
except Exception as e:
    st.error(f"Error fetching ThingSpeak data: {e}")
    st.stop()

if df.empty:
    st.warning("No data returned from ThingSpeak. Check channel/read key.")
    st.stop()

# Main layout: chart + table
col_chart, col_table = st.columns([3,1])

with col_chart:
    st.subheader("Live Air Quality (field1)")
    fig = px.line(df, x='created_at', y='field1', title='Air Quality (field1)', labels={'created_at':'Time','field1':'AirQuality'})
    fig.update_xaxes(rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("Latest")
    latest_val = df['field1'].iloc[-1]
    latest_ts = timestamp_to_local_str(df['created_at'].iloc[-1])
    st.metric("Latest value", f"{latest_val:.3f}" if pd.notna(latest_val) else "N/A")
    st.write("Timestamp")
    st.write(latest_ts)
    st.write(f"Points fetched: {len(df)}")
    if 'field2' in df.columns:
        st.write("Field2 sample (maybe humidity):", df['field2'].dropna().tail(1).iloc[0] if not df['field2'].dropna().empty else "N/A")
    if 'field3' in df.columns:
        st.write("Field3 sample (maybe temperature):", df['field3'].dropna().tail(1).iloc[0] if not df['field3'].dropna().empty else "N/A")

st.subheader("Recent Data (tail)")
st.dataframe(df[['created_at','field1','field2','field3']].tail(200).reset_index(drop=True))

# AI summary panel
st.markdown("## AI Summary (local Ollama)")
max_pts = st.slider("Use last how many points for summary?", min_value=5, max_value=min(500, len(df)), value=min(50, len(df)))
if st.button("Generate AI Summary (Ollama)"):
    prompt = prepare_prompt(df, max_points=max_pts)
    st.info("Calling Ollama... this may take a few seconds")
    with st.spinner("Generating summary via Ollama..."):
        summary = call_ollama(prompt, model=ollama_model, ollama_url=ollama_url)
    st.success("AI Summary")
    st.write(summary)

# Auto-refresh: sleep then rerun (simple local approach)
st.caption(f"Auto-refresh every {poll} seconds. The page will reload to fetch fresh data.")
time.sleep(poll)
st.experimental_rerun()
