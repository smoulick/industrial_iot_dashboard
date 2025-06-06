import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from pathlib import Path

# --- MUST BE THE FIRST STREAMLIT COMMAND ---
st.set_page_config(page_title="Conveyor Belt Monitoring", layout="wide")

CONVEYOR_DATA_DIR = Path("data_output/conveyor_belt")
REFRESH_INTERVAL_MS = 2000  # 2 seconds

# Auto-refresh every 2 seconds, does NOT reset scroll!
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="datarefresh")
st.title("Conveyor Belt Monitoring Dashboard")

# --- Sidebar with dropdown ---
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
    except FileNotFoundError:
        st.error(f"Data file not found for {sensor_name}!")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {sensor_name} data: {str(e)}")
        return pd.DataFrame()

if component == "Default":
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🔄 Inductive Sensor")
        df_inductive = load_sensor_data(
            CONVEYOR_DATA_DIR / "inductive_NBN40-CB1-PRESENCE_data.csv",
            "Inductive Sensor"
        )
        if not df_inductive.empty:
            latest = df_inductive.iloc[0]
            st.metric("Detection State", "OBJECT" if latest['output_state'] else "CLEAR")
            st.metric("Distance", f"{latest['distance_to_target_mm']:.1f} mm")
            st.metric("Switching Function", latest['switching_function'])
            st.line_chart(df_inductive.set_index('timestamp')['distance_to_target_mm'].tail(100))
            with st.expander("📥 Show Recent Inductive Readings", expanded=False):
                show_cols = [c for c in ['timestamp', 'distance_to_target_mm', 'output_state', 'switching_function'] if c in df_inductive.columns]
                if show_cols:
                    st.dataframe(
                        df_inductive.head(10)[show_cols].set_index('timestamp'),
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.info("No matching columns for Inductive Sensor table.")
        else:
            st.info("No data for Inductive Sensor.")

    with col2:
        st.subheader("📏 Ultrasonic Sensor")
        df_ultrasonic = load_sensor_data(
            CONVEYOR_DATA_DIR / "ultrasonic_UB800-CB1-MAIN_data.csv",
            "Ultrasonic Sensor"
        )
        if not df_ultrasonic.empty:
            latest = df_ultrasonic.iloc[0]
            st.metric("Measured Distance", f"{latest['distance_mm']:.1f} mm")
            st.metric("Detection State", "OBJECT PRESENT" if latest['output_state'] else "NO OBJECT")
            st.metric("Switching Events", f"{latest['switching_events']}")
            st.metric("Production Phase", latest['production_phase'])
            st.line_chart(df_ultrasonic.set_index('timestamp')['distance_mm'].sort_index().tail(100))
            with st.expander("📥 Show Recent Ultrasonic Readings", expanded=False):
                show_cols = [
                    c for c in [
                        'timestamp', 'distance_mm', 'output_state',
                        'switching_events', 'production_phase'
                    ] if c in df_ultrasonic.columns
                ]
                if show_cols:
                    st.dataframe(
                        df_ultrasonic.head(10)[show_cols].set_index('timestamp'),
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.info("No matching columns for Ultrasonic Sensor table.")
        else:
            st.info("No data for Ultrasonic Sensor.")

    with col3:
        st.subheader("🌡️ Heat Sensor")
        df_heat = load_sensor_data(
            CONVEYOR_DATA_DIR / "heat_PATOL5450-CB1-HOTSPOT_data.csv",
            "Heat Sensor"
        )
        if not df_heat.empty:
            latest = df_heat.iloc[0]
            st.metric("Material Temperature", f"{latest['simulated_material_temp_c']:.1f}°C")
            st.metric("Fire Alarm", "TRIPPED" if latest['fire_alarm_state'] else "NORMAL")
            st.metric("Fault Status", "FAULT" if latest['fault_state'] else "OK")
            st.line_chart(df_heat.set_index('timestamp')['simulated_material_temp_c'].tail(100))
            with st.expander("📥 Show Recent Heat Readings", expanded=False):
                show_cols = [c for c in ['timestamp', 'simulated_material_temp_c', 'fire_alarm_state', 'fault_state'] if c in df_heat.columns]
                if show_cols:
                    st.dataframe(
                        df_heat.head(10)[show_cols].set_index('timestamp'),
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.info("No matching columns for Heat Sensor table.")
        else:
            st.info("No data for Heat Sensor.")

    st.divider()
    # Conveyor Belt Touchswitch TS2V4AI
    st.subheader("🔧 Conveyor Belt Alignment (4B Touchswitch)")
    df_touchswitch_conv = load_sensor_data(
        CONVEYOR_DATA_DIR / "touchswitch_conveyor.csv",
        "Conveyor Touchswitch"
    )
    if not df_touchswitch_conv.empty:
        latest = df_touchswitch_conv.iloc[0]
        col1, col2 = st.columns(2)
        col1.metric("Alignment Status", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
        col2.metric("Alerts", latest['alerts'])
        with st.expander("📥 Recent Conveyor Alignment Data"):
            st.dataframe(
                df_touchswitch_conv[['timestamp', 'alignment_status', 'alerts']].set_index('timestamp').head(10),
                use_container_width=True
            )
    else:
        st.info("No conveyor alignment data available.")

elif component == "Idler/Roller (Smart-Idler)":
    st.subheader("Idler/Roller Monitoring (Smart-Idler)")
    df_idler = load_sensor_data(
        CONVEYOR_DATA_DIR / "smart_idler_data.csv",
        "Smart-Idler"
    )
    if not df_idler.empty:
        required_cols = ['timestamp', 'rpm', 'temp_left', 'temp_right',
                         'vibration_rms', 'BPFI', 'BPFO', 'BSF', 'FTF', 'alerts']
        if all(col in df_idler.columns for col in required_cols):
            latest = df_idler.iloc[0]
            cols = st.columns(4)
            cols[0].metric("RPM", f"{latest['rpm']:.1f}")
            cols[1].metric("Left Temp", f"{latest['temp_left']:.1f}°C")
            cols[2].metric("Right Temp", f"{latest['temp_right']:.1f}°C")
            cols[3].metric("Vibration", f"{latest['vibration_rms']:.2f} g")

            alert_status = st.empty()
            if latest['alerts'] != "NORMAL":
                alert_status.error(f"🚨 Active Alerts: {latest['alerts']}")
            else:
                alert_status.success("✅ All systems normal")

            col1, col2 = st.columns(2)
            with col1:
                st.caption("RPM Trend")
                st.line_chart(df_idler.set_index('timestamp')['rpm'].tail(200))

            with col2:
                st.caption("Bearing Temperatures")
                st.line_chart(df_idler.set_index('timestamp')[['temp_left', 'temp_right']].tail(200))

            st.caption("Vibration Frequencies")
            vib_cols = st.columns(4)
            vib_cols[0].metric("BPFI", f"{latest['BPFI']:.2f}")
            vib_cols[1].metric("BPFO", f"{latest['BPFO']:.2f}")
            vib_cols[2].metric("BSF", f"{latest['BSF']:.2f}")
            vib_cols[3].metric("FTF", f"{latest['FTF']:.2f}")

            with st.expander("📥 Recent Readings"):
                st.dataframe(df_idler[required_cols].head(10).set_index('timestamp'))
        else:
            st.error("Smart-Idler data format mismatch!")
    else:
        st.info("No Smart-Idler data available.")

elif component == "Pulley":
    st.subheader("🔧 Pulley Alignment (4B Touchswitch)")
    df_touchswitch_pulley = load_sensor_data(
        CONVEYOR_DATA_DIR / "touchswitch_pulley.csv",
        "Pulley Touchswitch"
    )
    if not df_touchswitch_pulley.empty:
        latest = df_touchswitch_pulley.iloc[0]
        col1, col2 = st.columns(2)
        col1.metric("Alignment Status", "MISALIGNED 🔴" if latest['alignment_status'] else "OK ✅")
        col2.metric("Relay Status", "ALARM" if latest['relay_status'] == 0 else "NORMAL")
        with st.expander("📥 Recent Pulley Alignment Data"):
            st.dataframe(
                df_touchswitch_pulley[['timestamp', 'alignment_status', 'relay_status', 'operational_mode']].set_index('timestamp').head(10),
                use_container_width=True
            )
    else:
        st.info("No pulley alignment data available.")

    # Incremental Encoder under Pulley
    st.subheader("🔧 Incremental Encoder Monitoring")
    df_encoder = load_sensor_data(
        CONVEYOR_DATA_DIR / "incremental_encoder_data.csv",
        "Incremental Encoder"
    )
    if not df_encoder.empty:
        required_cols = ['timestamp', 'rpm', 'pulse_count', 'direction', 'status']
        if all(col in df_encoder.columns for col in required_cols):
            latest = df_encoder.iloc[0]
            cols = st.columns(3)
            cols[0].metric("RPM", f"{latest['rpm']:.1f}")
            cols[1].metric("Direction", latest['direction'])
            cols[2].metric("Total Pulses", f"{latest['pulse_count']:,}")
            if latest['status'] != "NORMAL":
                st.error(f"Encoder Status: {latest['status']}")
            else:
                st.success("Encoder Status: NORMAL")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("RPM Trend (Last 100 Samples)")
                st.line_chart(df_encoder.set_index('timestamp')['rpm'].tail(100))
            with col2:
                st.caption("Pulse Accumulation")
                st.line_chart(df_encoder.set_index('timestamp')['pulse_count'].tail(100))
            with st.expander("📥 Recent Encoder Readings"):
                st.dataframe(df_encoder[required_cols].head(10).set_index('timestamp'))
        else:
            st.error("Encoder data format mismatch!")
    else:
        st.info("No encoder data available.")

current_time = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
st.divider()
st.caption(f"Last Updated: {current_time} | Refresh Interval: {REFRESH_INTERVAL_MS // 1000}s")
