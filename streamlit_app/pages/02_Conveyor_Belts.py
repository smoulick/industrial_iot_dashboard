import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Conveyor Belt Monitoring", layout="wide")

st.markdown("""<style>
    html { scroll-behavior: smooth; }
    .block-container { padding-top: 1rem; }
</style>""", unsafe_allow_html=True)

CONVEYOR_DATA_DIR = Path("data_output/conveyor_belt")
REFRESH_INTERVAL_MS = 2000  # 2 seconds

st_autorefresh(interval=REFRESH_INTERVAL_MS, key="datarefresh")
st.title("Conveyor Belt Monitoring Dashboard")

with st.sidebar:
    st.title("Conveyor Components")
    component = st.selectbox(
        "Select Component",
        ["Default", "Idler/Roller (Smart-Idler)", "Pulley"]
    )

def load_sensor_data(file_path, sensor_name):
    try:
        df = pd.read_csv(file_path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values('timestamp', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading {sensor_name} data: {e}")
        return pd.DataFrame()

def live_anomaly_detection(data, feature_cols):
    if len(data) < 20:
        return None, None
    features = data[feature_cols].fillna(method='ffill')
    scaler = StandardScaler().fit(features)
    model = IsolationForest(contamination=0.05, random_state=42).fit(scaler.transform(features))
    scores = model.decision_function(scaler.transform(features))
    anomalies = model.predict(scaler.transform(features))
    return scores, anomalies

def live_rul_prediction(data, feature_cols, event_col):
    if len(data) < 20:
        return None
    data = data.copy()
    data['rul'] = 100 - data[event_col].cumsum()
    features = data[feature_cols].fillna(0)
    target = data['rul'].clip(lower=0)
    model = xgb.XGBRegressor(n_estimators=100, random_state=42)
    model.fit(features, target)
    predictions = model.predict(features)
    return predictions

# ========== DEFAULT COMPONENT ==========
if component == "Default":

    # ---------- INDUCTIVE ----------
    with st.container():
        st.subheader("🔄 Inductive Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "inductive_NBN40-CB1-PRESENCE_data.csv", "Inductive Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Distance", f"{latest['distance_to_target_mm']:.1f} mm")
            st.metric("Detection", "OBJECT" if latest['output_state'] else "CLEAR")
            st.line_chart(df.set_index('timestamp')['distance_to_target_mm'].tail(100))
        else:
            st.warning("No Inductive data")

    # ---------- ULTRASONIC ----------
    with st.container():
        st.subheader("📏 Ultrasonic Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "ultrasonic_UB800-CB1-MAIN_data.csv", "Ultrasonic Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Distance", f"{latest['distance_mm']:.1f} mm")
            st.metric("Switches", latest['switching_events'])
            st.line_chart(df.set_index('timestamp')['distance_mm'].tail(100))
        else:
            st.warning("No Ultrasonic data")

    # ---------- HEAT SENSOR ----------
    with st.container():
        st.subheader("🌡️ Heat Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "heat_PATOL5450-CB1-HOTSPOT_data.csv", "Heat Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Temp", f"{latest['simulated_material_temp_c']:.1f}°C")
            st.metric("Fire Alarm", "TRIPPED" if latest['fire_alarm_state'] else "NORMAL")
            st.line_chart(df.set_index('timestamp')['simulated_material_temp_c'].tail(100))
        else:
            st.warning("No Heat Sensor data")

    # ---------- TOUCHSWITCH CONVEYOR ----------
    with st.container():
        st.subheader("🔧 Conveyor Belt Alignment (Touchswitch)")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "touchswitch_conveyor.csv", "Conveyor Touchswitch")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Alignment", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
            st.metric("Alerts", latest['alerts'])

            # Add chart if time series data exists
            if 'timestamp' in df.columns and 'alignment_status' in df.columns:
                df_plot = df.copy()
                df_plot['alignment_status'] = df_plot['alignment_status'].astype(int)
                st.line_chart(df_plot.set_index('timestamp')['alignment_status'].tail(100))

            # Add table
            with st.expander("📥 Recent Alignment Records"):
                st.dataframe(df[['timestamp', 'alignment_status', 'alerts']].head(20).set_index('timestamp'))

        else:
            st.warning("No Touchswitch Conveyor data")



# ========== SMART-IDLER ==========
elif component == "Idler/Roller (Smart-Idler)":
    st.subheader("🛞 Smart Idler Monitoring")
    df = load_sensor_data(CONVEYOR_DATA_DIR / "smart_idler_data.csv", "Smart-Idler")
    if not df.empty:
        latest = df.iloc[0]
        cols = st.columns(4)
        cols[0].metric("RPM", f"{latest['rpm']:.1f}")
        cols[1].metric("Left Temp", f"{latest['temp_left']:.1f}°C")
        cols[2].metric("Right Temp", f"{latest['temp_right']:.1f}°C")
        cols[3].metric("Vibration", f"{latest['vibration_rms']:.2f} g")
        with st.expander("🤖 ML: Anomaly + RUL"):
            scores, anomalies = live_anomaly_detection(df, ['rpm', 'vibration_rms', 'temp_left', 'temp_right'])
            if scores is not None:
                df['anomaly_score'] = scores
                df['is_anomaly'] = anomalies
                st.plotly_chart(px.line(df, x='timestamp', y='anomaly_score', title="Anomaly Score"))
                st.metric("Status", "🚨 Anomaly" if df.iloc[0]['is_anomaly'] == -1 else "✅ Normal")
                predictions = live_rul_prediction(df, ['rpm', 'vibration_rms', 'temp_left', 'temp_right'], 'vibration_rms')
                if predictions is not None:
                    st.plotly_chart(px.line(df, x='timestamp', y=predictions, title="RUL Trend"))
                    st.metric("RUL", f"{predictions[0]:.1f}")
            else:
                st.info("Need 20+ rows for ML")
            st.dataframe(df.head(20).set_index('timestamp'))
    else:
        st.warning("No Smart-Idler data")

# ========== PULLEY COMPONENT ==========
elif component == "Pulley":
    # --- Touchswitch ---
    with st.container():
        st.subheader("🔧 Pulley Alignment (Touchswitch)")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "touchswitch_pulley.csv", "Pulley Touchswitch")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Alignment", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
            st.metric("Relay", "ALARM" if latest['relay_status'] == 0 else "NORMAL")
            with st.expander("🤖 ML: Anomaly + RUL"):
                scores, anomalies = live_anomaly_detection(df, ['measured_force', 'operational_mode'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.plotly_chart(px.line(df, x='timestamp', y='anomaly_score', title="Anomaly Score"))
                    st.metric("Status", "🚨 Anomaly" if df.iloc[0]['is_anomaly'] == -1 else "✅ Normal")
                    predictions = live_rul_prediction(df, ['measured_force', 'operational_mode', 'thermal_fuse_blown'], 'alignment_status')
                    if predictions is not None:
                        st.plotly_chart(px.line(df, x='timestamp', y=predictions, title="RUL Trend"))
                        st.metric("RUL", f"{predictions[0]:.1f}")
                else:
                    st.info("Need 20+ rows for ML")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No pulley alignment data")

    # --- Encoder ---
    with st.container():
        st.subheader("🔁 Incremental Encoder")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "incremental_encoder_data.csv", "Encoder")
        if not df.empty:
            latest = df.iloc[0]
            cols = st.columns(3)
            cols[0].metric("RPM", f"{latest['rpm']:.1f}")
            cols[1].metric("Direction", latest['direction'])
            cols[2].metric("Pulses", latest['pulse_count'])
            with st.expander("🤖 ML: Anomaly + RUL"):
                scores, anomalies = live_anomaly_detection(df, ['rpm', 'pulse_count'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.plotly_chart(px.line(df, x='timestamp', y='anomaly_score', title="Anomaly Score"))
                    st.metric("Status", "🚨 Anomaly" if df.iloc[0]['is_anomaly'] == -1 else "✅ Normal")
                    predictions = live_rul_prediction(df, ['rpm', 'pulse_count'], 'rpm')
                    if predictions is not None:
                        st.plotly_chart(px.line(df, x='timestamp', y=predictions, title="RUL Trend"))
                        st.metric("RUL", f"{predictions[0]:.1f}")
                else:
                    st.info("Need 20+ rows for ML")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No encoder data")

# Footer
st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refresh every {REFRESH_INTERVAL_MS//1000}s")
