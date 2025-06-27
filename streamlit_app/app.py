import streamlit as st

st.set_page_config(
    page_title="Mining Health Monitoring",
    page_icon="⛏️",
    layout="wide"
)

st.title("🛠️ Industrial Health Monitoring Dashboard")
st.markdown("Welcome to the monitoring system for **Conveyor Belts** and **Ball Mills**.")
st.divider()
st.page_link("pages/01_Conveyor_Belt.py", label="🚛 Conveyor Belt Dashboard", icon="🔗")
