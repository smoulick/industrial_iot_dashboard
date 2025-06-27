import streamlit as st

# ✅ MUST BE FIRST Streamlit command
st.set_page_config(page_title="Conveyor Belt Monitoring", layout="wide")
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
from pathlib import Path

css_path = Path(__file__).parent.parent / "assets" / "styles.css"
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
st.title("Conveyor Belt Monitoring Dashboard")

CONVEYOR_DATA_DIR = Path("data_output/conveyor_belt")

# Default Sensors
INDUCTIVE_PATH = CONVEYOR_DATA_DIR / "inductive_NBN40-CB1-PRESENCE_data.csv"
ULTRASONIC_PATH = CONVEYOR_DATA_DIR / "ultrasonic_UB800-CB1-MAIN_data.csv"
HEAT_PATH = CONVEYOR_DATA_DIR / "heat_PATOL5450-CB1-HOTSPOT_data.csv"
TOUCHSWITCH_CONVEYOR_PATH = CONVEYOR_DATA_DIR / "touchswitch_conveyor.csv"

# Idler
SMART_IDLER_PATH = CONVEYOR_DATA_DIR / "smart_idler_data.csv"

# Pulley
TOUCHSWITCH_PULLEY_PATH = CONVEYOR_DATA_DIR / "touchswitch_pulley.csv"
PULLEY_ENCODER_PATH = CONVEYOR_DATA_DIR / "pulley_incremental_encoder.csv"

# Impact Bed
IMPACT_LOADCELL_PATH = CONVEYOR_DATA_DIR / "impact_bed_load_cell.csv"
IMPACT_ACCEL_PATH = CONVEYOR_DATA_DIR / "impact_bed_accelerometer.csv"


component = st.sidebar.selectbox(
    "Select Component",
    [
        "Default",
        "Idler/Roller",
        "Pulley",
        "Impact Bed"
    ]
)


def load_sensor_data(file_path):
    try:
        df = pd.read_csv(file_path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values('timestamp')
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
    rul = []
    event_indices = df.index[df[event_col] == 1].tolist()
    n = len(df)
    for i in range(n):
        future_events = [idx for idx in event_indices if idx >= i]
        rul.append(future_events[0] - i if future_events else n - i - 1)
    return rul

# --------------------------------------
# DEFAULT SECTION (Dropdown for sensors)
# --------------------------------------

if component == "Default":
    default_sensor = st.selectbox(
        "Select Sensor",
        ["Inductive", "Ultrasonic", "Heat", "Touchswitch Conveyor"]
    )

    # ------------------ 🔄 Inductive Sensor ------------------
    if default_sensor == "Inductive":
        path = CONVEYOR_DATA_DIR / "inductive_NBN40-CB1-PRESENCE_data.csv"
        if path.exists():
            df = load_sensor_data(path)
            df['event'] = df['output_state']
            df['rul'] = calculate_rul(df, event_col='event')

            st.subheader("🔄 Inductive Sensor (NBN40-U1-E2-V1)")
            with st.expander("Inject Anomaly"):
                with st.form("inject_inductive"):
                    distance = st.number_input("Distance to Target (mm)", value=60.0)
                    output_state = st.selectbox("Output State", [0, 1])
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "distance_to_target_mm": distance,
                            "output_state": output_state,
                            "event": output_state
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            st.metric("Distance to Target (mm)", f"{df.iloc[-1]['distance_to_target_mm']:.2f}")
            st.line_chart(df.set_index("timestamp")["distance_to_target_mm"].tail(100))

            with st.expander("ML Insights"):
                scores, anomalies = live_anomaly_detection(df, ['distance_to_target_mm'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))

            df['threshold_anomaly'] = df['distance_to_target_mm'] > 80
            styled = df.tail(30).style.apply(lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r), axis=1)
            st.dataframe(styled, use_container_width=True)

    # ------------------ 📏 Ultrasonic Sensor ------------------
    elif default_sensor == "Ultrasonic":
        path = CONVEYOR_DATA_DIR / "ultrasonic_UB800-CB1-MAIN_data.csv"
        if path.exists():
            df = load_sensor_data(path)
            df['event'] = df['output_state']
            df['rul'] = calculate_rul(df, event_col='event')

            st.subheader("📏 Ultrasonic Sensor (UB800-18GM60-E5-V1-M)")
            with st.expander("Inject Anomaly"):
                with st.form("inject_ultrasonic"):
                    distance = st.number_input("Distance (mm)", value=900.0)
                    output_state = st.selectbox("Output State", [0, 1])
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "distance_mm": distance,
                            "output_state": output_state,
                            "event": output_state
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            st.metric("Distance (mm)", f"{df.iloc[-1]['distance_mm']:.1f}")
            st.line_chart(df.set_index("timestamp")["distance_mm"].tail(100))

            with st.expander("ML Insights"):
                scores, anomalies = live_anomaly_detection(df, ['distance_mm'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))

            df['threshold_anomaly'] = df['distance_mm'] > 800
            styled = df.tail(30).style.apply(lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r), axis=1)
            st.dataframe(styled, use_container_width=True)

    # ------------------ 🌡️ Heat Sensor ------------------
    elif default_sensor == "Heat":
        path = CONVEYOR_DATA_DIR / "heat_PATOL5450-CB1-HOTSPOT_data.csv"
        if path.exists():
            df = load_sensor_data(path)
            df['event'] = df['fire_alarm_state']
            df['rul'] = calculate_rul(df, event_col='event')

            st.subheader("🌡️ Heat Sensor (PATOL5450)")
            with st.expander("Inject Anomaly"):
                with st.form("inject_heat"):
                    temp = st.number_input("Material Temp (°C)", value=105.0)
                    fire_alarm = st.selectbox("Fire Alarm State", [0, 1])
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "simulated_material_temp_c": temp,
                            "fire_alarm_state": fire_alarm,
                            "event": fire_alarm
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            st.metric("Material Temp (°C)", f"{df.iloc[-1]['simulated_material_temp_c']:.2f}")
            st.line_chart(df.set_index("timestamp")["simulated_material_temp_c"].tail(100))

            with st.expander("ML Insights"):
                scores, anomalies = live_anomaly_detection(df, ['simulated_material_temp_c'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))

            df['threshold_anomaly'] = df['simulated_material_temp_c'] > 100
            styled = df.tail(30).style.apply(lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r), axis=1)
            st.dataframe(styled, use_container_width=True)

    # ------------------ 🔧 Touchswitch Conveyor ------------------
    elif default_sensor == "Touchswitch Conveyor":
        path = CONVEYOR_DATA_DIR / "touchswitch_conveyor.csv"
        if path.exists():
            df = load_sensor_data(path)
            df['event'] = df['alignment_status']
            df['rul'] = calculate_rul(df, event_col='event')

            st.subheader("🔧 Touchswitch Conveyor (TS2V4AI)")
            with st.expander("Inject Anomaly"):
                with st.form("inject_touchswitch"):
                    force = st.number_input("Measured Force (kg)", value=4.0)
                    align = st.selectbox("Alignment Status", [0, 1])
                    mode = st.selectbox("Operational Mode", [0, 1])
                    fuse = st.selectbox("Thermal Fuse Blown", [0, 1])
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "measured_force": force,
                            "alignment_status": align,
                            "operational_mode": mode,
                            "thermal_fuse_blown": fuse,
                            "event": align
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            st.metric("Measured Force (kg)", f"{df.iloc[-1]['measured_force']:.2f}")
            st.line_chart(df.set_index("timestamp")["measured_force"].tail(100))

            with st.expander("ML Insights"):
                scores, anomalies = live_anomaly_detection(df, ['measured_force', 'operational_mode'])
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))

            df['threshold_anomaly'] = (df['alignment_status'] == 1) | (df['thermal_fuse_blown'] == 1)
            styled = df.tail(30).style.apply(lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r), axis=1)
            st.dataframe(styled, use_container_width=True)


# --------------------------------------
# SMART IDLER SECTION
# --------------------------------------
elif component == "Idler/Roller":
    path = CONVEYOR_DATA_DIR / "smart_idler_data.csv"
    if path.exists():
        df = load_sensor_data(path)

        st.subheader("🟢 Smart Idler Sensor (Vayeron SI-OFBA-6309)")
        df['event'] = (df['vibration_rms'] > 1.5) | (df['temp_left'] > 80) | (df['temp_right'] > 80)
        df['event'] = df['event'].astype(int)
        df['rul'] = calculate_rul(df, event_col='event')

        with st.expander("Inject Anomaly"):
            with st.form("inject_idler"):
                rpm = st.number_input("RPM", value=1200.0)
                temp_left = st.number_input("Left Temp (°C)", value=70.0)
                temp_right = st.number_input("Right Temp (°C)", value=70.0)
                vibration_rms = st.number_input("Vibration RMS (g)", value=1.2)
                BPFI = st.number_input("BPFI", value=0.05)
                BPFO = st.number_input("BPFO", value=0.05)
                BSF = st.number_input("BSF", value=0.05)
                FTF = st.number_input("FTF", value=0.05)
                alerts = st.text_input("Alerts", value="VIBRATION_HIGH")
                submit = st.form_submit_button("Inject")
                if submit:
                    new_row = df.iloc[-1].copy()
                    new_row.update({
                        "timestamp": datetime.now().isoformat(),
                        "rpm": rpm,
                        "temp_left": temp_left,
                        "temp_right": temp_right,
                        "vibration_rms": vibration_rms,
                        "BPFI": BPFI,
                        "BPFO": BPFO,
                        "BSF": BSF,
                        "FTF": FTF,
                        "alerts": alerts,
                        "event": int(vibration_rms > 1.5 or temp_left > 80 or temp_right > 80)
                    })
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(path, index=False)
                    st.success("Anomaly injected.")
                    st.rerun()

        # Show metrics
        st.metric("RPM", f"{df.iloc[-1]['rpm']:.0f}")
        st.metric("Vibration RMS (g)", f"{df.iloc[-1]['vibration_rms']:.3f}")
        st.metric("Left Temp (°C)", f"{df.iloc[-1]['temp_left']:.1f}")
        st.metric("Right Temp (°C)", f"{df.iloc[-1]['temp_right']:.1f}")

        # Plot trends
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.line(df, x="timestamp", y="vibration_rms", title="Vibration RMS Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.line(df, x="timestamp", y="rpm", title="RPM Over Time")
            st.plotly_chart(fig2, use_container_width=True)

        # ML Insights
        with st.expander("ML Insights"):
            features = ['rpm', 'vibration_rms', 'temp_left', 'temp_right']
            scores, anomalies = live_anomaly_detection(df, features)
            if scores is not None:
                df['anomaly_score'] = scores
                df['is_anomaly'] = anomalies
                st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                st.line_chart(df.set_index("timestamp")["rul"].tail(100))

        # Highlight abnormal rows
        df['threshold_anomaly'] = df['event'] == 1
        styled = df.tail(30).style.apply(
            lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r),
            axis=1
        )
        st.dataframe(styled, use_container_width=True)


# --------------------------------------
# PULLEY SECTION (Encoder + Touchswitch)
# --------------------------------------
elif component == "Pulley":
    pulley_sensor = st.selectbox("Select Pulley Sensor", ["Touchswitch Pulley", "Incremental Encoder"])

    if pulley_sensor == "Touchswitch Pulley":
        path = CONVEYOR_DATA_DIR / "touchswitch_pulley.csv"
        if path.exists():
            df = load_sensor_data(path)

            st.subheader("🟠 Pulley – Touchswitch Sensor (TS2V4AI)")

            # Define event: misalignment or thermal fuse blown
            df['event'] = (df['alignment_status'] == 1) | (df['thermal_fuse_blown'] == 1)
            df['event'] = df['event'].astype(int)
            df['rul'] = calculate_rul(df, event_col='event')

            # Fault Injection
            with st.expander("Inject Anomaly"):
                with st.form("inject_touchswitch_pulley"):
                    alignment = st.selectbox("Alignment Status", [0, 1])
                    fuse = st.selectbox("Thermal Fuse Blown", [0, 1])
                    force = st.number_input("Measured Force (kg)", value=4.0)
                    mode = st.selectbox("Operational Mode", [0, 1])
                    relay = st.selectbox("Relay Status", [0, 1])
                    led = st.selectbox("LED Status", [0, 1])
                    alerts = st.text_input("Alerts", value="MISALIGNMENT")
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "alignment_status": alignment,
                            "thermal_fuse_blown": fuse,
                            "measured_force": force,
                            "operational_mode": mode,
                            "relay_status": relay,
                            "led_status": led,
                            "alerts": alerts,
                            "event": int(alignment == 1 or fuse == 1)
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            # Show Metrics
            latest = df.iloc[-1]
            st.metric("Measured Force (kg)", f"{latest['measured_force']:.2f}")
            st.metric("Alignment Status", "❌ Misaligned" if latest['alignment_status'] == 1 else "✅ Aligned")
            st.metric("Thermal Fuse", "🔥 Blown" if latest['thermal_fuse_blown'] == 1 else "✅ Intact")
            st.metric("RUL (rows)", f"{latest['rul']}")

            # Time Series Plots
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.line(df, x="timestamp", y="measured_force", title="Measured Force Over Time")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.line(df, x="timestamp", y="operational_mode", title="Operational Mode")
                st.plotly_chart(fig2, use_container_width=True)

            # ML Insights
            with st.expander("ML Insights"):
                features = ['measured_force', 'operational_mode']
                scores, anomalies = live_anomaly_detection(df, features)
                if scores is not None:
                    df['anomaly_score'] = scores
                    df['is_anomaly'] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))
                else:
                    st.info("Need at least 20 rows for ML.")

            # Highlight anomalies
            df["threshold_anomaly"] = (df["alignment_status"] == 1) | (df["thermal_fuse_blown"] == 1)
            styled = df.tail(30).style.apply(
                lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r),
                axis=1
            )
            st.dataframe(styled, use_container_width=True)

    elif component == "Pulley":
        path = CONVEYOR_DATA_DIR / "pulley_incremental_encoder.csv"
        if path.exists():
            df = load_sensor_data(path)

            st.subheader("🟠 Pulley – Incremental Encoder")

            # Define event column based on 'status' (e.g., abnormal = "ERROR")
            df['event'] = (df['status'].str.upper() == "ERROR").astype(int)
            df['rul'] = calculate_rul(df, event_col='event')

            # Fault injection
            with st.expander("Inject Anomaly"):
                with st.form("inject_pulley_encoder"):
                    rpm = st.number_input("RPM", value=1200.0)
                    pulse_count = st.number_input("Pulse Count", value=30000)
                    direction = st.selectbox("Direction", ["Forward", "Reverse"])
                    status = st.text_input("Status", value="OK")  # e.g., OK / ERROR / NO_SIGNAL
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "rpm": rpm,
                            "pulse_count": pulse_count,
                            "direction": direction,
                            "status": status,
                            "event": int(status.upper() == "ERROR")
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            # Show metrics
            latest = df.iloc[-1]
            st.metric("RPM", f"{latest['rpm']:.1f}")
            st.metric("Pulse Count", f"{latest['pulse_count']}")
            st.metric("Direction", f"{latest['direction']}")
            st.metric("RUL (rows)", f"{latest['rul']}")

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.line(df, x="timestamp", y="rpm", title="RPM Over Time")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.line(df, x="timestamp", y="pulse_count", title="Pulse Count Over Time")
                st.plotly_chart(fig2, use_container_width=True)

            # ML Insights
            with st.expander("ML Insights"):
                features = ["rpm", "pulse_count"]
                scores, anomalies = live_anomaly_detection(df, features)
                if scores is not None:
                    df["anomaly_score"] = scores
                    df["is_anomaly"] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]["is_anomaly"] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))
                else:
                    st.info("Need at least 20 data points for ML.")

            # Highlight abnormal rows
            df["threshold_anomaly"] = df["status"].str.upper() == "ERROR"
            styled = df.tail(30).style.apply(
                lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r),
                axis=1
            )
            st.dataframe(styled, use_container_width=True)

# --------------------------------------
# IMPACT BED SECTION (Load Cell + Accelerometer)
# --------------------------------------
elif component == "Impact Bed":
    impact_sensor = st.selectbox("Select Impact Bed Sensor", ["Load Cell", "Accelerometer"])

    if impact_sensor == "Load Cell":
       path = CONVEYOR_DATA_DIR / "impact_bed_load_cell.csv"
       if path.exists():
        df = load_sensor_data(path)

        st.subheader("🔵 Impact Bed – Load Cell")

        # Add event + RUL
        df['event'] = df['impact_event']
        df['rul'] = calculate_rul(df, event_col='event')

        # Fault injection
        with st.expander("Inject Anomaly"):
            with st.form("inject_impact_loadcell"):
                load = st.number_input("Applied Load (kN)", value=1200.0)
                mv_per_v = st.number_input("mV/V Output", value=2.0)
                excitation = st.number_input("Excitation Voltage (V)", value=10.0)
                temp = st.number_input("Sensor Temperature (°C)", value=30.0)
                impact_event = st.selectbox("Impact Event", [0, 1])
                alerts = st.text_input("Alerts", value="NORMAL")
                submit = st.form_submit_button("Inject")
                if submit:
                    new_row = df.iloc[-1].copy()
                    new_row.update({
                        "timestamp": datetime.now().isoformat(),
                        "applied_load_kN": load,
                        "mv_per_v": mv_per_v,
                        "excitation_V": excitation,
                        "temperature_C": temp,
                        "impact_event": impact_event,
                        "alerts": alerts,
                        "event": impact_event
                    })
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(path, index=False)
                    st.success("Anomaly injected.")
                    st.rerun()

        # Latest metrics
        latest = df.iloc[-1]
        st.metric("Applied Load (kN)", f"{latest['applied_load_kN']:.1f}")
        st.metric("Excitation (V)", f"{latest['excitation_V']:.2f}")
        st.metric("Sensor Temp (°C)", f"{latest['temperature_C']:.1f}")
        st.metric("RUL (rows)", f"{latest['rul']}")

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.line(df, x="timestamp", y="applied_load_kN", title="Applied Load Over Time")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.line(df, x="timestamp", y="mv_per_v", title="mV/V Output Over Time")
            st.plotly_chart(fig2, use_container_width=True)

        # ML Insights
        with st.expander("ML Insights"):
            features = ["applied_load_kN", "mv_per_v", "temperature_C"]
            scores, anomalies = live_anomaly_detection(df, features)
            if scores is not None:
                df["anomaly_score"] = scores
                df["is_anomaly"] = anomalies
                st.metric("Anomaly", "🚨" if df.iloc[-1]["is_anomaly"] == -1 else "✅")
                st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                st.line_chart(df.set_index("timestamp")["rul"].tail(100))
            else:
                st.info("Need at least 20 data points for ML.")

        # Highlight abnormal rows
        df["threshold_anomaly"] = df["impact_event"] == 1
        styled = df.tail(30).style.apply(
            lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r),
            axis=1
        )
        st.dataframe(styled, use_container_width=True)

    elif component == "Impact Bed":
        path = CONVEYOR_DATA_DIR / "impact_bed_accelerometer.csv"
        if path.exists():
            df = load_sensor_data(path)

            st.subheader("🟣 Impact Bed – Accelerometer (ADXL1001)")

            # Add event + RUL
            df['event'] = df['impact_event']
            df['rul'] = calculate_rul(df, event_col='event')

            # Fault injection
            with st.expander("Inject Anomaly"):
                with st.form("inject_impact_accel"):
                    accel_x = st.number_input("Accel X (g)", value=2.0)
                    vib_rms = st.number_input("Vibration RMS (g)", value=3.0)
                    impact_peak = st.number_input("Impact Peak (g)", value=50.0)
                    impact_event = st.selectbox("Impact Event", [0, 1])
                    overrange = st.selectbox("Overrange", [0, 1])
                    alerts = st.text_input("Alerts", value="IMPACT DETECTED")
                    submit = st.form_submit_button("Inject")
                    if submit:
                        new_row = df.iloc[-1].copy()
                        new_row.update({
                            "timestamp": datetime.now().isoformat(),
                            "accel_x_g": accel_x,
                            "vibration_rms_g": vib_rms,
                            "impact_peak_g": impact_peak,
                            "impact_event": impact_event,
                            "overrange": overrange,
                            "alerts": alerts,
                            "event": impact_event
                        })
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_csv(path, index=False)
                        st.success("Anomaly injected.")
                        st.rerun()

            # Latest metrics
            latest = df.iloc[-1]
            st.metric("Accel X (g)", f"{latest['accel_x_g']:.2f}")
            st.metric("Vibration RMS (g)", f"{latest['vibration_rms_g']:.2f}")
            st.metric("Impact Peak (g)", f"{latest['impact_peak_g']:.2f}")
            st.metric("RUL (rows)", f"{latest['rul']}")

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.line(df, x="timestamp", y="accel_x_g", title="Accel X (g) Over Time")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.line(df, x="timestamp", y="vibration_rms_g", title="Vibration RMS Over Time")
                st.plotly_chart(fig2, use_container_width=True)

            # ML Insights
            with st.expander("ML Insights"):
                features = ["accel_x_g", "vibration_rms_g"]
                scores, anomalies = live_anomaly_detection(df, features)
                if scores is not None:
                    df["anomaly_score"] = scores
                    df["is_anomaly"] = anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[-1]["is_anomaly"] == -1 else "✅")
                    st.line_chart(df.set_index("timestamp")["anomaly_score"].tail(100))
                    st.line_chart(df.set_index("timestamp")["rul"].tail(100))
                else:
                    st.info("Need at least 20 data points for ML.")

            # Highlight abnormal rows
            df["threshold_anomaly"] = df["impact_event"] == 1
            styled = df.tail(30).style.apply(
                lambda r: ['background-color: #ffcccc' if r['threshold_anomaly'] else ''] * len(r),
                axis=1
            )
            st.dataframe(styled, use_container_width=True)

# --------------------------------------
st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
