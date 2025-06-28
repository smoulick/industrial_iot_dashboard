import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import streamlit as st
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="Ball Mill Monitoring", layout="wide")
# 🔄 Auto-refresh every 10 seconds (10000 ms)
st_autorefresh(interval=10000, limit=None, key="ball_mill_autorefresh")
import pandas as pd
import plotly.express as px
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from pathlib import Path
from utils.hf_loader import download_from_huggingface
# Always resolve paths inside streamlit_app/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data_output"
BALL_MILL_DATA_DIR = DATA_DIR / "ball_mill"

HF_BASE = "https://huggingface.co/spaces/smoulick/industrial-iot-data/resolve/main/data_output/ball_mill"

# Local paths
BALL_MILL_DATA_DIR = Path("data_output/ball_mill")
GRINDCONTROL_PATH = BALL_MILL_DATA_DIR / "retsch_grindcontrol_data.csv"
VIBRATION_PATH = BALL_MILL_DATA_DIR / "mill_shell_vibration_data.csv"
ACOUSTIC_PATH = BALL_MILL_DATA_DIR / "mill_shell_acoustic_data.csv"
MOTOR_ACCEL_PATH = BALL_MILL_DATA_DIR / "motor_accelerometer_data.csv"
MOTOR_TEMP_PATH = BALL_MILL_DATA_DIR / "motor_temperature_data.csv"

# Download files if missing
download_from_huggingface(GRINDCONTROL_PATH, f"{HF_BASE}/retsch_grindcontrol_data.csv")
download_from_huggingface(VIBRATION_PATH, f"{HF_BASE}/mill_shell_vibration_data.csv")
download_from_huggingface(ACOUSTIC_PATH, f"{HF_BASE}/mill_shell_acoustic_data.csv")
download_from_huggingface(MOTOR_ACCEL_PATH, f"{HF_BASE}/motor_accelerometer_data.csv")
download_from_huggingface(MOTOR_TEMP_PATH, f"{HF_BASE}/motor_temperature_data.csv")

# Load CSVs
grind_df = pd.read_csv(GRINDCONTROL_PATH)
vib_df = pd.read_csv(VIBRATION_PATH)
acoustic_df = pd.read_csv(ACOUSTIC_PATH)
motor_accel_df = pd.read_csv(MOTOR_ACCEL_PATH)
motor_temp_df = pd.read_csv(MOTOR_TEMP_PATH)

css_path = Path(__file__).parent.parent / "assets" / "styles.css"
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

component = st.selectbox(
    "Select Component",
    [
        "Grinding Jar",
        "Mill Shell",
        "Motor",
        "Feed System",
        "Drive System"
    ]
)

def load_sensor_data(file_path):
    try:
        df = pd.read_csv(file_path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values('timestamp', ascending=False)
        return df
    except Exception as e:
        st.error(f"[load_sensor_data Error] {e}")
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

def calculate_rul(df, event_col='event'):
    """Calculate Remaining Useful Life (RUL) for each row based on the event column."""
    rul = []
    event_indices = df.index[df[event_col] == 1].tolist()
    n = len(df)
    for i in range(n):
        # Find the next event after this row
        future_events = [idx for idx in event_indices if idx >= i]
        if future_events:
            next_event = future_events[0]
            rul.append(next_event - i)
        else:
            rul.append(n - i - 1)
    return rul

# ------------------- Grinding Jar -------------------
if component == "Grinding Jar":
    if GRINDCONTROL_PATH.exists():
        df = load_sensor_data(GRINDCONTROL_PATH)
        st.write(f"Loaded {len(df)} rows from {GRINDCONTROL_PATH}")

        st.header("Grinding Jar")
        st.subheader("Retsch GrindControl (Temperature & Pressure)")

        # Fault Injection
        with st.expander("Inject Anomaly (Grinding Jar - Retsch GrindControl)"):
            with st.form("inject_anomaly_grinding_jar"):
                temperature_c = st.number_input("Temperature (°C) [abnormal: >80]", min_value=-25.0, max_value=120.0, value=30.0)
                pressure_bar = st.number_input("Pressure (bar) [abnormal: >4.5]", min_value=0.0, max_value=6.0, value=1.0)
                event = st.selectbox("Event (0=Normal, 1=Fault) [abnormal: 1]", [0, 1])
                submit = st.form_submit_button("Inject")
                if submit:
                    if df.empty:
                        st.warning("Cannot inject fault: no existing data.")
                    else:
                        new_row = df.iloc[-1].to_dict()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "temperature_c": temperature_c,
                            "pressure_bar": pressure_bar,
                            "event": event
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(GRINDCONTROL_PATH, index=False)
                        st.success("Anomaly injected!")
                        st.rerun()

        # Show latest values
        latest = df.iloc[-1]
        st.metric("Temperature (°C)", f"{latest['temperature_c']:.2f}")
        st.metric("Pressure (bar)", f"{latest['pressure_bar']:.3f}")

        # Plot time series
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Temperature Trend")
            fig1 = px.line(df, x="timestamp", y="temperature_c", title="Temperature (°C) Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.subheader("Pressure Trend")
            fig2 = px.line(df, x="timestamp", y="pressure_bar", title="Pressure (bar) Over Time")
            st.plotly_chart(fig2, use_container_width=True)

        # ML Insights (Anomaly + RUL)
        with st.expander("ML Insights (Anomaly & RUL)", expanded=True):
            feature_cols = ['temperature_c', 'pressure_bar']
            scores, anomalies = live_anomaly_detection(df, feature_cols)
            if scores is not None:
                df['anomaly_score'] = scores
                df['is_anomaly'] = anomalies
                st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                st.line_chart(df.set_index('timestamp')['anomaly_score'].tail(100))
            else:
                st.info("Need 20+ rows for ML.")

            # RUL (already present in data)
            if 'event' in df.columns:
                df['rul'] = calculate_rul(df, event_col='event')
                st.metric("RUL (rows)", f"{df.iloc[-1]['rul']}")
                st.line_chart(df.set_index('timestamp')['rul'].tail(100))

        # Highlight anomalies
        df['threshold_anomaly'] = (df['temperature_c'] > 80) | (df['pressure_bar'] > 4.5)
        st.write("### Recent Data")
        def highlight_row(row):
            color = 'background-color: #ffcccc' if row['threshold_anomaly'] else ''
            return [color] * len(row)
        styled = df.tail(30).style.apply(highlight_row, axis=1)
        st.dataframe(styled, use_container_width=True)
    else:
        st.error(f"Data file not found: {GRINDCONTROL_PATH}")

# ------------------- Mill Shell (Vibration & Temperature) -------------------
elif component == "Mill Shell":
    if VIBRATION_PATH.exists():
        df = load_sensor_data(VIBRATION_PATH)
        st.write(f"Loaded {len(df)} rows from {VIBRATION_PATH}")

        st.header("Mill Shell")
        st.subheader("Vibration & Temperature Sensor")

        # Add event column if not present
        if 'event' not in df.columns:
            df['event'] = ((df['vibration_g'] > 7) | (df['temperature_c'] > 80)).astype(int)
        df['rul'] = calculate_rul(df, event_col='event')

        # Fault Injection
        with st.expander("Inject Anomaly (Mill Shell Vibration)"):
            with st.form("inject_anomaly_mill_shell"):
                vibration_g = st.number_input("Vibration (g) [abnormal: >7]", min_value=0.0, max_value=15.0, value=2.0)
                temperature_c = st.number_input("Temperature (°C) [abnormal: >80]", min_value=20.0, max_value=120.0, value=30.0)
                submit = st.form_submit_button("Inject")
                if submit:
                    if df.empty:
                        st.warning("Cannot inject fault: no existing data.")
                    else:
                        new_row = df.iloc[-1].to_dict()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "vibration_g": vibration_g,
                            "temperature_c": temperature_c,
                            "event": int((vibration_g > 7) or (temperature_c > 80))
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(VIBRATION_PATH, index=False)
                        st.success("Anomaly injected!")
                        st.rerun()

        # Show latest values
        latest = df.iloc[-1]
        st.metric("Vibration (g)", f"{latest['vibration_g']:.3f}")
        st.metric("Temperature (°C)", f"{latest['temperature_c']:.2f}")
        st.metric("RUL (rows)", f"{latest['rul']}")

        # Plot time series
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Vibration Trend")
            fig1 = px.line(df, x="timestamp", y="vibration_g", title="Vibration (g) Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.subheader("Temperature Trend")
            fig2 = px.line(df, x="timestamp", y="temperature_c", title="Temperature (°C) Over Time")
            st.plotly_chart(fig2, use_container_width=True)

        # ML Insights (Anomaly Detection & RUL)
        with st.expander("ML Insights (Anomaly Detection & RUL)", expanded=True):
            feature_cols = ['vibration_g', 'temperature_c']
            scores, anomalies = live_anomaly_detection(df, feature_cols)
            if scores is not None:
                df['anomaly_score'] = scores
                df['is_anomaly'] = anomalies
                st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                st.line_chart(df.set_index('timestamp')['anomaly_score'].tail(100))
                st.line_chart(df.set_index('timestamp')['rul'].tail(100))
            else:
                st.info("Need 20+ rows for ML.")

        # Highlight anomalies
        df['threshold_anomaly'] = (df['vibration_g'] > 7) | (df['temperature_c'] > 80)
        st.write("### Recent Data")
        def highlight_row(row):
            color = 'background-color: #ffcccc' if row['threshold_anomaly'] else ''
            return [color] * len(row)
        styled = df.tail(30).style.apply(highlight_row, axis=1)
        st.dataframe(styled, use_container_width=True)

    # ---- Mill Shell Acoustic Sensor ----
    if ACOUSTIC_PATH.exists():
        df_acoustic = load_sensor_data(ACOUSTIC_PATH)
        st.subheader("Acoustic Sensor (Sound & Fill Level)")

        # Add event and RUL columns if not present
        if 'event' not in df_acoustic.columns:
            df_acoustic['event'] = ((df_acoustic['sound_db'] > 100) | (df_acoustic['fill_level_pct'] > 110)).astype(int)
        df_acoustic['rul'] = calculate_rul(df_acoustic, event_col='event')

        # Fault Injection
        with st.expander("Inject Anomaly (Mill Shell Acoustic)"):
            with st.form("inject_anomaly_mill_shell_acoustic"):
                sound_db = st.number_input("Sound Level (dB) [abnormal: >100]", min_value=50.0, max_value=130.0,
                                           value=70.0)
                fill_level_pct = st.number_input("Fill Level (%) [abnormal: >110]", min_value=0.0, max_value=130.0,
                                                 value=60.0)
                submit = st.form_submit_button("Inject")
                if submit:
                    if df_acoustic.empty:
                        st.warning("Cannot inject fault: no existing data.")
                    else:
                        new_row = df_acoustic.iloc[-1].to_dict()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "sound_db": sound_db,
                            "fill_level_pct": fill_level_pct,
                            "event": int((sound_db > 100) or (fill_level_pct > 110))
                        })
                        df_acoustic = pd.concat([df_acoustic, pd.DataFrame([new_row])], ignore_index=True)
                        df_acoustic.to_csv(ACOUSTIC_PATH, index=False)
                        st.success("Anomaly injected!")
                        st.rerun()

        # Show latest values
        latest = df_acoustic.iloc[-1]
        st.metric("Sound Level (dB)", f"{latest['sound_db']:.2f}")
        st.metric("Fill Level (%)", f"{latest['fill_level_pct']:.1f}")
        st.metric("RUL (rows)", f"{latest['rul']}")

        # Plot time series
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Sound Level Trend")
            fig1 = px.line(df_acoustic, x="timestamp", y="sound_db", title="Sound Level (dB) Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.subheader("Fill Level Trend")
            fig2 = px.line(df_acoustic, x="timestamp", y="fill_level_pct", title="Fill Level (%) Over Time")
            st.plotly_chart(fig2, use_container_width=True)

        # ML Insights (Anomaly Detection & RUL)
        with st.expander("ML Insights (Anomaly Detection & RUL)", expanded=True):
            feature_cols = ['sound_db', 'fill_level_pct']
            scores, anomalies = live_anomaly_detection(df_acoustic, feature_cols)
            if scores is not None:
                df_acoustic['anomaly_score'] = scores
                df_acoustic['is_anomaly'] = anomalies
                st.metric("Anomaly", "🚨" if df_acoustic.iloc[-1]['is_anomaly'] == -1 else "✅")
                st.line_chart(df_acoustic.set_index('timestamp')['anomaly_score'].tail(100))
                st.line_chart(df_acoustic.set_index('timestamp')['rul'].tail(100))
            else:
                st.info("Need 20+ rows for ML.")

        # Highlight anomalies
        df_acoustic['threshold_anomaly'] = (df_acoustic['sound_db'] > 100) | (df_acoustic['fill_level_pct'] > 110)
        st.write("### Recent Data")


        def highlight_row_acoustic(row):
            color = 'background-color: #ffcccc' if row['threshold_anomaly'] else ''
            return [color] * len(row)


        styled_acoustic = df_acoustic.tail(30).style.apply(highlight_row_acoustic, axis=1)
        st.dataframe(styled_acoustic, use_container_width=True)
    else:
        st.error(f"Data file not found: {ACOUSTIC_PATH}")

# ------------------- Motor (3-Axis Accelerometer) -------------------
elif component == "Motor":
    if MOTOR_ACCEL_PATH.exists():
        df = load_sensor_data(MOTOR_ACCEL_PATH)
        st.write(f"Loaded {len(df)} rows from {MOTOR_ACCEL_PATH}")

        st.header("Motor")
        st.subheader("3-Axis Accelerometer Sensor")

        # Add event column if not present
        if 'event' not in df.columns:
            df['event'] = ((df['accel_x_g'].abs() > 7) | (df['accel_y_g'].abs() > 7) | (df['accel_z_g'].abs() > 7)).astype(int)
        df['rul'] = calculate_rul(df, event_col='event')

        # Fault Injection
        with st.expander("Inject Anomaly (Motor Accelerometer)"):
            with st.form("inject_anomaly_motor_accel"):
                accel_x = st.number_input("Acceleration X (g) [abnormal: >7 or < -7]", min_value=-15.0, max_value=15.0, value=0.0)
                accel_y = st.number_input("Acceleration Y (g) [abnormal: >7 or < -7]", min_value=-15.0, max_value=15.0, value=0.0)
                accel_z = st.number_input("Acceleration Z (g) [abnormal: >7 or < -7]", min_value=-15.0, max_value=15.0, value=0.0)
                submit = st.form_submit_button("Inject")
                if submit:
                    if df.empty:
                        st.warning("Cannot inject fault: no existing data.")
                    else:
                        new_row = df.iloc[-1].to_dict()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "accel_x_g": accel_x,
                            "accel_y_g": accel_y,
                            "accel_z_g": accel_z,
                            "event": int((abs(accel_x) > 7) or (abs(accel_y) > 7) or (abs(accel_z) > 7))
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(MOTOR_ACCEL_PATH, index=False)
                        st.success("Anomaly injected!")
                        st.rerun()

        # Show latest values
        latest = df.iloc[-1]
        st.metric("Acceleration X (g)", f"{latest['accel_x_g']:.4f}")
        st.metric("Acceleration Y (g)", f"{latest['accel_y_g']:.4f}")
        st.metric("Acceleration Z (g)", f"{latest['accel_z_g']:.4f}")
        st.metric("RUL (rows)", f"{latest['rul']}")

        # Plot time series
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Acceleration X Trend")
            fig1 = px.line(df, x="timestamp", y="accel_x_g", title="Acceleration X (g) Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.subheader("Acceleration Y Trend")
            fig2 = px.line(df, x="timestamp", y="accel_y_g", title="Acceleration Y (g) Over Time")
            st.plotly_chart(fig2, use_container_width=True)
        with col3:
            st.subheader("Acceleration Z Trend")
            fig3 = px.line(df, x="timestamp", y="accel_z_g", title="Acceleration Z (g) Over Time")
            st.plotly_chart(fig3, use_container_width=True)

        # ML Insights (Anomaly Detection & RUL)
        with st.expander("ML Insights (Anomaly Detection & RUL)", expanded=True):
            feature_cols = ['accel_x_g', 'accel_y_g', 'accel_z_g']
            scores, anomalies = live_anomaly_detection(df, feature_cols)
            if scores is not None:
                df['anomaly_score'] = scores
                df['is_anomaly'] = anomalies
                st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                st.line_chart(df.set_index('timestamp')['anomaly_score'].tail(100))
                st.line_chart(df.set_index('timestamp')['rul'].tail(100))
            else:
                st.info("Need 20+ rows for ML.")

        # Highlight anomalies
        df['threshold_anomaly'] = (df['accel_x_g'].abs() > 7) | (df['accel_y_g'].abs() > 7) | (df['accel_z_g'].abs() > 7)
        st.write("### Recent Data")
        def highlight_row(row):
            color = 'background-color: #ffcccc' if row['threshold_anomaly'] else ''
            return [color] * len(row)
        styled = df.tail(30).style.apply(highlight_row, axis=1)
        st.dataframe(styled, use_container_width=True)
    else:
        st.error(f"Data file not found: {MOTOR_ACCEL_PATH}")

        # ---- Motor Temperature Sensor ----
    if MOTOR_TEMP_PATH.exists():
            df_temp = load_sensor_data(MOTOR_TEMP_PATH)
            st.subheader("Motor Temperature Sensor")

            # Add event and RUL columns if not present
            if 'event' not in df_temp.columns:
                df_temp['event'] = (df_temp['temperature_c'] > 110).astype(int)  # Example threshold
            df_temp['rul'] = calculate_rul(df_temp, event_col='event')

            # Fault Injection
            with st.expander("Inject Anomaly (Motor Temperature)"):
                with st.form("inject_anomaly_motor_temp"):
                    temperature_c = st.number_input("Temperature (°C) [abnormal: >110]", min_value=-40.0,
                                                    max_value=200.0, value=40.0)
                    submit = st.form_submit_button("Inject")
                    if submit:
                        if df_temp.empty:
                            st.warning("Cannot inject fault: no existing data.")
                        else:
                            new_row = df_temp.iloc[-1].to_dict()
                            new_row.update({
                                "timestamp": datetime.now().isoformat(),
                                "temperature_c": temperature_c,
                                "event": int(temperature_c > 110)
                            })
                            df_temp = pd.concat([df_temp, pd.DataFrame([new_row])], ignore_index=True)
                            df_temp.to_csv(MOTOR_TEMP_PATH, index=False)
                            st.success("Anomaly injected!")
                            st.rerun()

            # Show latest values
            latest = df_temp.iloc[-1]
            st.metric("Temperature (°C)", f"{latest['temperature_c']:.2f}")
            st.metric("RUL (rows)", f"{latest['rul']}")

            # Plot time series
            st.subheader("Temperature Trend")
            fig = px.line(df_temp, x="timestamp", y="temperature_c", title="Motor Temperature (°C) Over Time")
            st.plotly_chart(fig, use_container_width=True)

            # ML Insights (Anomaly Detection & RUL)
            with st.expander("ML Insights (Anomaly Detection & RUL)", expanded=True):
                feature_cols = ['temperature_c']
                scores, anomalies = live_anomaly_detection(df_temp, feature_cols)
                if scores is not None:
                    df_temp['anomaly_score'] = scores
                    df_temp['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df_temp.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df_temp.set_index('timestamp')['anomaly_score'].tail(100))
                    st.line_chart(df_temp.set_index('timestamp')['rul'].tail(100))
                else:
                    st.info("Need 20+ rows for ML.")

            # Highlight anomalies
            df_temp['threshold_anomaly'] = (df_temp['temperature_c'] > 110)
            st.write("### Recent Data")


            def highlight_row_temp(row):
                color = 'background-color: #ffcccc' if row['threshold_anomaly'] else ''
                return [color] * len(row)


            styled_temp = df_temp.tail(30).style.apply(highlight_row_temp, axis=1)
            st.dataframe(styled_temp, use_container_width=True)
    else:
         st.error(f"Data file not found: {MOTOR_TEMP_PATH}")

else:
    st.info("Component not implemented yet. Please select 'Grinding Jar', 'Mill Shell', or 'Motor'.")
