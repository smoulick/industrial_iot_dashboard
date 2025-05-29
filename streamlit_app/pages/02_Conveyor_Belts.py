# D:\Project\industrial_iot_dashboard\streamlit_app\pages\02_Conveyor_Belts.py
import streamlit as st
import pandas as pd
from pathlib import Path
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Conveyor Belt Monitoring",
    page_icon="🚚",
    layout="wide"
)

# --- Page Title ---
st.title("🚚 Conveyor Belt Monitoring")

# --- Path to the CSV file ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONVEYOR_DATA_DIR = PROJECT_ROOT / "data_output" / "conveyor_belt"


# --- Function to load data (reused) ---
def load_sensor_data(file_path: Path, sensor_type: str):
    # print(f"[STREAMLIT DEBUG] load_sensor_data for {sensor_type} from: {file_path}")
    if file_path.exists():
        if file_path.stat().st_size > 0:
            try:
                df = pd.read_csv(file_path)
                if not df.empty:
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    else:
                        st.error(f"'{sensor_type}' CSV missing 'timestamp' column: {file_path.name}")
                        return pd.DataFrame()
                return df
            except pd.errors.EmptyDataError:
                return pd.DataFrame() # File is empty
            except Exception as e:
                st.error(f"Error loading '{sensor_type}' data from '{file_path.name}': {e}")
                return pd.DataFrame()
        else:
            return pd.DataFrame() # File exists but is 0 bytes
    else:
        return pd.DataFrame() # File does not exist

# === Ultrasonic Sensor Section ===
st.header("Ultrasonic Sensor Data")
ULTRASONIC_CSV_FILENAME = "ultrasonic_UB800-CB1-MAIN_data.csv" # Match your config
ULTRASONIC_DATA_FILE_PATH = CONVEYOR_DATA_DIR / ULTRASONIC_CSV_FILENAME
ultrasonic_placeholder = st.empty()

# === Inductive Sensor Section ===
st.divider()
st.header("Inductive Sensor Data")
INDUCTIVE_SENSOR_FILES = {
    "NBN40-CB1-PRESENCE": "inductive_NBN40-CB1-PRESENCE_data.csv",
    "NBN40-CB1-LIMIT": "inductive_NBN40-CB1-LIMIT_data.csv"
}
inductive_placeholders = {key: st.empty() for key in INDUCTIVE_SENSOR_FILES}


# === Heat Sensor Section ===
st.divider()
st.header("Infrared Heat Sensor Data (Patol 5450)")
HEAT_SENSOR_FILES = {
    "PATOL5450-CB1-HOTSPOT": "heat_PATOL5450-CB1-HOTSPOT_data.csv"
}
heat_sensor_placeholders = {key: st.empty() for key in HEAT_SENSOR_FILES}


# --- Main Display Loop ---
while True:
    # --- Update Ultrasonic Sensor Display ---
    df_ultrasonic = load_sensor_data(ULTRASONIC_DATA_FILE_PATH, "Ultrasonic")
    with ultrasonic_placeholder.container():
        st.subheader(f"Ultrasonic: {ULTRASONIC_CSV_FILENAME}")
        if not df_ultrasonic.empty:
            required_us_cols = ['timestamp', 'sensor_id', 'distance_mm', 'output', 'mode']
            if not all(col in df_ultrasonic.columns for col in required_us_cols):
                st.error(f"Ultrasonic CSV missing required columns.")
            else:
                latest_us_point = df_ultrasonic.iloc[-1]
                us_cols = st.columns(5)
                us_cols[0].metric("Time", latest_us_point['timestamp'].strftime('%H:%M:%S'))
                us_cols[1].metric("Sensor ID", str(latest_us_point['sensor_id']))
                us_cols[2].metric("Distance (mm)", f"{latest_us_point['distance_mm']:.2f}")
                us_cols[3].metric("Output", "ON" if latest_us_point['output'] == 1 else "OFF")
                us_cols[4].metric("Mode", str(latest_us_point['mode']))

                st.caption("Recent Ultrasonic Readings (Time Series Data)")
                st.dataframe(df_ultrasonic.tail(5).set_index('timestamp'), use_container_width=True)

                st.caption("Ultrasonic Distance Over Time") # Caption for the chart
                st.line_chart(df_ultrasonic.set_index('timestamp')[['distance_mm']].tail(200), use_container_width=True) # Chart restored, showing last 200 points
        else:
            st.caption(f"No data for Ultrasonic Sensor ({ULTRASONIC_CSV_FILENAME}).")

    # --- Update Inductive Sensor(s) Display ---
    for sensor_id_key, inductive_csv_filename in INDUCTIVE_SENSOR_FILES.items():
        inductive_data_file_path = CONVEYOR_DATA_DIR / inductive_csv_filename
        df_inductive = load_sensor_data(inductive_data_file_path, f"Inductive ({sensor_id_key})")

        with inductive_placeholders[sensor_id_key].container():
            st.subheader(f"Inductive: {inductive_csv_filename} (ID: {sensor_id_key})")
            if not df_inductive.empty:
                required_ind_cols = ['timestamp', 'sensor_id', 'distance_to_target_mm', 'output_state', 'switching_function']
                if not all(col in df_inductive.columns for col in required_ind_cols):
                     st.error(f"Inductive CSV for {sensor_id_key} missing required columns.")
                else:
                    latest_ind_point = df_inductive.iloc[-1]
                    ind_cols = st.columns(5)
                    ind_cols[0].metric("Time", latest_ind_point['timestamp'].strftime('%H:%M:%S'))
                    ind_cols[1].metric("Sensor ID", str(latest_ind_point['sensor_id']))
                    ind_cols[2].metric("Target Dist (mm)", f"{latest_ind_point['distance_to_target_mm']:.2f}")
                    ind_cols[3].metric("Output", "DETECTED" if latest_ind_point['output_state'] == (1 if latest_ind_point['switching_function'] == "NO" else 0) else "NOT DETECTED")
                    ind_cols[4].metric("Switch Func", str(latest_ind_point['switching_function']))

                    st.caption(f"Recent Inductive Readings ({sensor_id_key}) (Time Series Data)")
                    st.dataframe(df_inductive.tail(5).set_index('timestamp'), use_container_width=True)

                    st.caption(f"Inductive Target Distance Over Time ({sensor_id_key})") # Caption for the chart
                    st.line_chart(df_inductive.set_index('timestamp')[['distance_to_target_mm']].tail(200), use_container_width=True) # Chart added, showing last 200 points
            else:
                st.caption(f"No data for Inductive Sensor ({inductive_csv_filename}).")

    # --- Update Heat Sensor(s) Display ---
    for sensor_id_key, heat_csv_filename in HEAT_SENSOR_FILES.items():
        heat_data_file_path = CONVEYOR_DATA_DIR / heat_csv_filename
        df_heat = load_sensor_data(heat_data_file_path, f"Heat Sensor ({sensor_id_key})")

        with heat_sensor_placeholders[sensor_id_key].container():
            st.subheader(f"Heat Sensor: {heat_csv_filename} (ID: {sensor_id_key})")
            if not df_heat.empty:
                required_heat_cols = ["timestamp", "sensor_id", "simulated_material_temp_c", "fire_alarm_state", "fault_state", "green_led_normal_status", "red_led_trip_status"]
                if not all(col in df_heat.columns for col in required_heat_cols):
                    st.error(f"Heat Sensor CSV for {sensor_id_key} missing required columns.")
                else:
                    latest_heat_point = df_heat.iloc[-1]
                    hs_cols = st.columns(6)
                    hs_cols[0].metric("Time", latest_heat_point['timestamp'].strftime('%H:%M:%S'))
                    hs_cols[1].metric("Sensor ID", str(latest_heat_point['sensor_id']))
                    hs_cols[2].metric("Material Temp (°C)", f"{latest_heat_point['simulated_material_temp_c']:.1f}")

                    fire_status = "ALARM" if latest_heat_point['fire_alarm_state'] == 1 else "Normal"
                    hs_cols[3].metric("Fire Status", fire_status, delta_color=("inverse" if fire_status == "ALARM" else "off"))

                    fault_status = "FAULT" if latest_heat_point['fault_state'] == 1 else "OK"
                    hs_cols[4].metric("Sensor Fault", fault_status, delta_color=("inverse" if fault_status == "FAULT" else "off"))

                    led_status_text = []
                    if latest_heat_point['green_led_normal_status'] == 1: led_status_text.append("🟢 Normal")
                    if latest_heat_point['red_led_trip_status'] == 1: led_status_text.append("🔴 Trip")
                    if not led_status_text: led_status_text.append("LEDs Off")
                    hs_cols[5].markdown(f"**LEDs:** {', '.join(led_status_text)}")

                    st.caption(f"Recent Heat Sensor Readings ({sensor_id_key}) (Time Series Data)")
                    st.dataframe(df_heat.tail(5).set_index('timestamp'), use_container_width=True)

                    st.caption(f"Heat Sensor Material Temperature Over Time ({sensor_id_key})")
                    st.line_chart(df_heat.set_index('timestamp')[['simulated_material_temp_c']].tail(200), use_container_width=True) # Showing last 200 points
            else:
                st.caption(f"No data for Heat Sensor ({heat_csv_filename}).")

    time.sleep(2) # Refresh interval for the entire page