import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import numpy as np

st.set_page_config(page_title="Conveyor Belt Monitoring", layout="wide")

CONVEYOR_DATA_DIR = Path("data_output/conveyor_belt")
st.title("Conveyor Belt Monitoring Dashboard")
with st.sidebar:
    st.title("Conveyor Components")
    component = st.selectbox(
        "Select Component",
        [
            "Default",
            "Idler/Roller (Smart-Idler)",
            "Pulley",
            "Impact Bed"
        ]
    )
# Load CSV safely
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

# Inject fault into last n rows
def inject_fault_in_last_n_rows(df, inputs, n=5):
    for key, val in inputs.items():
        if key in df.columns:
            df.loc[:n, key] = val
    return df

# Anomaly Detection
def live_anomaly_detection(data, feature_cols):
    if len(data) < 20:
        return None, None
    features = data[feature_cols].copy().apply(pd.to_numeric, errors='coerce').fillna(0)
    scaler = StandardScaler().fit(features)
    model = IsolationForest(contamination=0.05, random_state=42).fit(scaler.transform(features))
    scores = model.decision_function(scaler.transform(features))
    anomalies = model.predict(scaler.transform(features))
    return scores, anomalies

# RUL Prediction
def live_rul_prediction(data, feature_cols, event_col):
    if len(data) < 20:
        return None
    data = data.copy()
    data[event_col] = pd.to_numeric(data[event_col], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)
    features = data[feature_cols].apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(0)
    data['rul'] = 100 - data[event_col].cumsum()
    target = data['rul'].clip(lower=0)
    mask = (~features.isna().any(axis=1)) & (~target.isna())
    features, target = features[mask], target[mask]
    if len(features) < 1:
        return None
    model = xgb.XGBRegressor(n_estimators=100, random_state=42)
    model.fit(features, target)
    predictions = model.predict(features)
    return predictions

# Generic Sensor Block
def sensor_section(sensor_label, file_name, inject_form, feature_cols, event_col=None, rul_features=None):
    try:
        st.subheader(sensor_label)
        file_path = CONVEYOR_DATA_DIR / file_name
        df = load_sensor_data(file_path)
        key_base = file_name.replace('.', '_')

        with st.expander(f"Inject Anomaly ({sensor_label})", expanded=True):
            with st.form(key=f"{key_base}_form"):
                inputs = inject_form()
                submit = st.form_submit_button("Inject")
                if submit:
                    if df.empty:
                        st.warning("Cannot inject fault: no existing data.")
                    else:
                        df = inject_fault_in_last_n_rows(df, inputs, n=5)
                        df.to_csv(file_path, index=False)
                        st.success("Anomaly injected!")
                        st.rerun()

        if df.empty:
            st.warning("No data available for this sensor.")
            return

        for col in feature_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        try:
            latest_val = df[feature_cols[0]].iloc[0]
            st.metric("Latest Reading", f"{latest_val:.2f}")
        except Exception as e:
            st.warning(f"Could not display metric: {e}")

        try:
            st.line_chart(df.set_index('timestamp')[feature_cols[0]].tail(100))
        except Exception as e:
            st.warning(f"Could not render chart: {e}")

        with st.expander("ML Insights (Anomaly & RUL)", expanded=False):
            try:
                scores, anomalies = live_anomaly_detection(df, feature_cols)
                if scores is not None:
                    df['anomaly_score'], df['is_anomaly'] = scores, anomalies
                    st.metric("Anomaly", "🚨" if df.iloc[0]['is_anomaly'] == -1 else "✅")
                    st.line_chart(df.set_index('timestamp')['anomaly_score'].tail(100))
                    if event_col and rul_features:
                        predictions = live_rul_prediction(df, rul_features, event_col)
                        if predictions is not None:
                            st.line_chart(pd.Series(predictions, index=df['timestamp'].head(len(predictions))))
                            st.metric("RUL", f"{predictions[0]:.1f}")
                else:
                    st.info("Need 20+ rows for ML.")
            except Exception as e:
                st.error(f"[ML Error] {sensor_label}: {e}")

        try:
            st.dataframe(df.head(20).set_index("timestamp"))
        except Exception as e:
            st.warning(f"Could not display table: {e}")

    except Exception as e:
        st.error(f"[Sensor Block Crash] {sensor_label}: {e}")

# ---------- DEFAULT SECTION ----------
if component == "Default":
    st.markdown("### 🟢 Default Section")

    default_sensor = st.selectbox(
        "Select Sensor to View",
        ["Inductive", "Ultrasonic", "Heat", "Touchswitch Conveyor"],
        key="default_sensor_select"
    )

    if default_sensor == "Inductive":
        try:
            sensor_section(
                sensor_label="🔄 Inductive Sensor",
                file_name="inductive_NBN40-CB1-PRESENCE_data.csv",
                inject_form=lambda: {
                    "distance_to_target": st.number_input("Distance to Target (mm)", value=50.0, key="inductive_distance"),
                    "output_state": st.selectbox("Output State", [0, 1], key="inductive_output")
                },
                feature_cols=["distance_to_target"],
                event_col="output_state",
                rul_features=["distance_to_target"]
            )
        except Exception as e:
            st.error(f"[Inductive Sensor Error] {e}")

    elif default_sensor == "Ultrasonic":
        try:
            sensor_section(
                sensor_label="📏 Ultrasonic Sensor",
                file_name="ultrasonic_UB800-CB1-MAIN_data.csv",
                inject_form=lambda: {
                    "distance_mm": st.number_input("Ultrasonic Distance (mm)", value=900.0, key="ultrasonic_distance"),
                    "output_state": st.selectbox("Ultrasonic Output State", [0, 1], key="ultrasonic_output")
                },
                feature_cols=["distance_mm"],
                event_col="output_state",
                rul_features=["distance_mm"]
            )
        except Exception as e:
            st.error(f"[Ultrasonic Sensor Error] {e}")

    elif default_sensor == "Heat":
        try:
            sensor_section(
                sensor_label="🌡️ Heat Sensor",
                file_name="heat_PATOL5450-CB1-HOTSPOT_data.csv",
                inject_form=lambda: {
                    "simulated_material_temp_c": st.number_input("Material Temp (°C)", value=120.0, key="heat_temp"),
                    "fire_alarm_state": st.selectbox("Fire Alarm State", [0, 1], key="heat_alarm")
                },
                feature_cols=["simulated_material_temp_c"],
                event_col="fire_alarm_state",
                rul_features=["simulated_material_temp_c"]
            )
        except Exception as e:
            st.error(f"[Heat Sensor Error] {e}")

    elif default_sensor == "Touchswitch Conveyor":
        try:
            sensor_section(
                sensor_label="🔧 Touchswitch Conveyor",
                file_name="touchswitch_conveyor.csv",
                inject_form=lambda: {
                    "measured_force": st.number_input("Measured Force (kg)", value=4.0, key="touch_force"),
                    "alignment_status": st.selectbox("Alignment Status", [0, 1], key="touch_align"),
                    "operational_mode": st.selectbox("Operational Mode", [0, 1], key="touch_mode"),
                    "thermal_fuse_blown": st.selectbox("Thermal Fuse Blown", [0, 1], key="touch_fuse")
                },
                feature_cols=["measured_force", "operational_mode"],
                event_col="alignment_status",
                rul_features=["measured_force", "operational_mode", "thermal_fuse_blown"]
            )
        except Exception as e:
            st.error(f"[Touchswitch Sensor Error] {e}")

# -------------------- SMART IDLER --------------------
elif component == "Idler/Roller (Smart-Idler)":
    sensor_section(
        "Smart Idler",
        "smart_idler_data.csv",
        lambda: {
            "rpm": st.number_input("RPM", value=2000.0),
            "temp_left": st.number_input("Left Temp (°C)", value=90.0),
            "temp_right": st.number_input("Right Temp (°C)", value=90.0),
            "vibration_rms": st.number_input("Vibration RMS", value=3.0),
            "BPFI": st.number_input("BPFI", value=0.0),
            "BPFO": st.number_input("BPFO", value=0.0),
            "BSF": st.number_input("BSF", value=0.0),
            "FTF": st.number_input("FTF", value=0.0),
            "alerts": st.text_input("Alerts", value="OVERHEAT")
        },
        feature_cols=["rpm", "vibration_rms", "temp_left", "temp_right"],
        event_col="vibration_rms",
        rul_features=["rpm", "vibration_rms", "temp_left", "temp_right"]
    )

# -------------------- PULLEY --------------------
elif component == "Pulley":
    sensor_section(
        "Touchswitch Pulley",
        "touchswitch_pulley.csv",
        lambda: {
            "measured_force": st.number_input("Measured Force (kg)", value=4.0),
            "alignment_status": st.selectbox("Alignment Status", [0, 1]),
            "operational_mode": st.selectbox("Operational Mode", [0, 1]),
            "relay_status": st.selectbox("Relay Status", [0, 1]),
            "thermal_fuse_blown": st.selectbox("Thermal Fuse Blown", [0, 1])
        },
        feature_cols=["measured_force", "operational_mode"],
        event_col="alignment_status",
        rul_features=["measured_force", "operational_mode", "thermal_fuse_blown"]
    )

    sensor_section(
        "Incremental Encoder",
        "incremental_encoder_data.csv",
        lambda: {
            "rpm": st.number_input("RPM", value=7000.0),
            "pulse_count": st.number_input("Pulse Count", value=100),
            "direction": st.selectbox("Direction", ["FORWARD", "REVERSE"]),
            "status": st.text_input("Status", value="FAULT")
        },
        feature_cols=["rpm", "pulse_count"],
        event_col="rpm",
        rul_features=["rpm", "pulse_count"]
    )

elif component == "Impact Bed":
    st.markdown("### 🟣 Impact Bed Section")

    impact_sensor = st.selectbox(
        "Select Impact Bed Sensor",
        ["Accelerometer", "Load Cell"],
        key="impact_sensor_select"
    )

    if impact_sensor == "Accelerometer":
        try:
            sensor_section(
                sensor_label="📈 Impact Bed Accelerometer",
                file_name="impact_bed_accelerometer.csv",
                inject_form=lambda: {
                    "accel_x_g": st.number_input("Accel X (g)", value=60.0, key="impact_accel_x"),
                    "vibration_rms_g": st.number_input("Vibration RMS (g)", value=60.0, key="impact_vib_rms"),
                    "impact_peak_g": st.number_input("Impact Peak (g)", value=60.0, key="impact_peak"),
                    "impact_event": st.selectbox("Impact Event", [0, 1], key="impact_event_accel")
                },
                feature_cols=["accel_x_g"],
                event_col="impact_event",
                rul_features=["accel_x_g"]
            )
        except Exception as e:
            st.error(f"[Impact Accelerometer Error] {e}")

    elif impact_sensor == "Load Cell":
        try:
            sensor_section(
                sensor_label="🪵 Impact Bed Load Cell",
                file_name="impact_bed_load_cell.csv",
                inject_form=lambda: {
                    "applied_load_kN": st.number_input("Applied Load (kN)", value=1200.0, key="impact_load"),
                    "mv_per_v": st.number_input("mV/V Output", value=0.0, key="impact_mv_per_v"),
                    "impact_event": st.selectbox("Impact Event", [0, 1], key="impact_event_load")
                },
                feature_cols=["applied_load_kN"],
                event_col="impact_event",
                rul_features=["applied_load_kN"]
            )
        except Exception as e:
            st.error(f"[Impact Load Cell Error] {e}")

# --- Footer ---
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.divider()
st.caption(f"Last Updated: {current_time}")

