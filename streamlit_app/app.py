from pathlib import Path
import streamlit as st

# MUST be first Streamlit command
st.set_page_config(
    page_title="Mining Health Monitoring",
    page_icon="⛏️",
    layout="wide"
)

# Load CSS (works regardless of where you run from)
css_path = Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🛠️ Industrial Health Monitoring Dashboard")
st.markdown("Welcome to the monitoring system for **Conveyor Belts** and **Ball Mills**.")
st.divider()

st.subheader("📂 Dashboards")
st.page_link("pages/01_Conveyor_Belts.py", label="🚛 Conveyor Belt Dashboard", icon="🟩")
st.page_link("pages/02_Ball_Mill.py", label="⚙️ Ball Mill Dashboard", icon="🟦")

