import streamlit as st

# MUST be first Streamlit command
st.set_page_config(
    page_title="Mining Health Monitoring",
    page_icon="⛏️",
    layout="wide"
)

# Optional CSS loader (if styles.css exists)
try:
    with open("assets/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except:
    pass

st.title("🛠️ Industrial Health Monitoring Dashboard")
st.markdown("Welcome to the monitoring system for **Conveyor Belts** and **Ball Mills**.")
st.divider()

st.subheader("📂 Dashboards")
st.page_link("pages/02_Conveyor_Belts.py", label="🚛 Conveyor Belt Dashboard", icon="🟩")
st.page_link("pages/03_Ball_Mill.py", label="⚙️ Ball Mill Dashboard", icon="🟦")
st.page_link("pages/01_Overview.py", label="📊 Project Overview", icon="📝")
