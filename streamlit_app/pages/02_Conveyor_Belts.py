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

# ----- Page Setup -----
st.set_page_config(page_title="Conveyor Belt Monitoring", layout="wide")
st.markdown("""<style>
    html { scroll-behavior: smooth; }
    .block-container { padding-top: 1rem; }
</style>""", unsafe_allow_html=True)

CONVEYOR_DATA_DIR = Path("data_output/conveyor_belt")
REFRESH_INTERVAL_MS = 2000  # 2 seconds refresh

st_autorefresh(interval=REFRESH_INTERVAL_MS, key="datarefresh")
st.title("Conveyor Belt Monitoring Dashboard")

with st.sidebar:
    st.title("Conveyor Components")
    component = st.selectbox("Select Component", ["Default", "Idler/Roller (Smart-Idler)", "Pulley"])

# ----- Utility Functions -----
def load_sensor_data(path, name):
    try:
        df = pd.read_csv(path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values('timestamp', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading {name}: {e}")
        return pd.DataFrame()

def live_anomaly_detection(df, features):
    if len(df) < 20: return None, None
    X = StandardScaler().fit_transform(df[features].fillna(method='ffill'))
    model = IsolationForest(contamination=0.05, random_state=42).fit(X)
    scores = model.decision_function(X)
    anns = model.predict(X)
    return scores, anns

def live_rul_prediction(df, features, evt):
    if len(df) < 20: return None
    df2 = df.copy()
    df2['rul'] = 100 - df2[evt].cumsum()
    X = df2[features].fillna(0)
    y = df2['rul'].clip(lower=0)
    model = xgb.XGBRegressor(n_estimators=100, random_state=42).fit(X, y)
    return model.predict(X)

# ----- Default Sensors Block -----
if component == "Default":

    # Inductive
    with st.container():
        st.subheader("🔄 Inductive Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "inductive_NBN40-CB1-PRESENCE_data.csv", "Inductive Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Distance", f"{latest['distance_to_target_mm']:.1f} mm")
            st.metric("Detection", "OBJECT" if latest['output_state'] else "CLEAR")
            st.line_chart(df.set_index('timestamp')['distance_to_target_mm'].tail(100))
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['distance_to_target_mm'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['distance_to_target_mm'], 'output_state')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Inductive data")

    # Ultrasonic
    with st.container():
        st.subheader("📏 Ultrasonic Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "ultrasonic_UB800-CB1-MAIN_data.csv", "Ultrasonic Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Distance", f"{latest['distance_mm']:.1f} mm")
            st.metric("Switches", latest['switching_events'])
            st.line_chart(df.set_index('timestamp')['distance_mm'].tail(100))
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['distance_mm'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['distance_mm'], 'output_state')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Ultrasonic data")

    # Heat
    with st.container():
        st.subheader("🌡️ Heat Sensor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "heat_PATOL5450-CB1-HOTSPOT_data.csv", "Heat Sensor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Temp", f"{latest['simulated_material_temp_c']:.1f}°C")
            st.metric("Fire Alarm", "TRIPPED" if latest['fire_alarm_state'] else "NORMAL")
            st.line_chart(df.set_index('timestamp')['simulated_material_temp_c'].tail(100))
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['simulated_material_temp_c'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['simulated_material_temp_c'], 'fire_alarm_state')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Heat data")

    # Touchswitch Conveyor
    with st.container():
        st.subheader("🔧 Touchswitch Conveyor")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "touchswitch_conveyor.csv", "Touchswitch Conveyor")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Alignment", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
            st.metric("Alerts", latest['alerts'])
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['measured_force', 'operational_mode'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['measured_force', 'operational_mode', 'thermal_fuse_blown'], 'alignment_status')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Touchswitch data")

# ----- SMART-IDLER -----
elif component == "Idler/Roller (Smart-Idler)":
    st.subheader("🛞 Smart Idler Monitoring")
    df = load_sensor_data(CONVEYOR_DATA_DIR / "smart_idler_data.csv", "Smart-Idler")
    if not df.empty:
        latest = df.iloc[0]
        st.metric("RPM", f"{latest['rpm']:.1f}")
        st.metric("Vibration", f"{latest['vibration_rms']:.2f} g")
        st.metric("Left Temp", f"{latest['temp_left']:.1f}°C")
        st.metric("Right Temp", f"{latest['temp_right']:.1f}°C")
        with st.expander("🤖 ML: Anomaly + RUL"):
            try:
                s, a = live_anomaly_detection(df, ['rpm', 'vibration_rms', 'temp_left', 'temp_right'])
                if s is not None:
                    df['an_score'], df['is_anomaly'] = s, a
                    st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                    st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                    preds = live_rul_prediction(df, ['rpm', 'vibration_rms', 'temp_left', 'temp_right'], 'vibration_rms')
                    if preds is not None:
                        st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                        st.metric("RUL", f"{preds[0]:.1f}")
                else: st.info("Need 20+ rows")
            except Exception as e:
                st.error(f"ML error: {e}")
            st.dataframe(df.head(20).set_index('timestamp'))
    else:
        st.warning("No Smart-Idler data")

# ----- PULLEY TOUCHSWITCH & ENCODER -----
elif component == "Pulley":

    # Touchswitch
    with st.container():
        st.subheader("🔧 Pulley Alignment (Touchswitch)")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "touchswitch_pulley.csv", "Pulley Touchswitch")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("Alignment", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
            st.metric("Relay", "ALARM" if latest['relay_status'] == 0 else "NORMAL")
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['measured_force', 'operational_mode'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['measured_force', 'operational_mode', 'thermal_fuse_blown'], 'alignment_status')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Pulley Touchswitch data")

    # Encoder
    with st.container():
        st.subheader("🔁 Incremental Encoder Monitoring")
        df = load_sensor_data(CONVEYOR_DATA_DIR / "incremental_encoder_data.csv", "Encoder")
        if not df.empty:
            latest = df.iloc[0]
            st.metric("RPM", f"{latest['rpm']:.1f}")
            st.metric("Direction", latest['direction'])
            st.metric("Pulses", latest['pulse_count'])
            with st.expander("🤖 ML: Anomaly + RUL"):
                try:
                    s, a = live_anomaly_detection(df, ['rpm', 'pulse_count'])
                    if s is not None:
                        df['an_score'], df['is_anomaly'] = s, a
                        st.plotly_chart(px.line(df, x='timestamp', y='an_score', title="Anomaly Score"))
                        st.metric("Status", "🚨 Anomaly" if a[0]==-1 else "✅ Normal")
                        preds = live_rul_prediction(df, ['rpm', 'pulse_count'], 'rpm')
                        if preds is not None:
                            st.plotly_chart(px.line(df, x='timestamp', y=preds, title="RUL Trend"))
                            st.metric("RUL", f"{preds[0]:.1f}")
                    else: st.info("Need 20+ rows")
                except Exception as e:
                    st.error(f"ML error: {e}")
                st.dataframe(df.head(20).set_index('timestamp'))
        else:
            st.warning("No Encoder data")

# ----- FOOTER -----
st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refresh: {REFRESH_INTERVAL_MS // 1000}s")
