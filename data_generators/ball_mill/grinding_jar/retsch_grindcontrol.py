import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

def generate_retsch_grindcontrol_data_stream(output_path, run_duration_seconds=None):
    TEMP_MIN, TEMP_MAX = -25, 90      # °C
    PRESSURE_MIN, PRESSURE_MAX = 0, 5 # bar
    time_interval_sec = 30  # seconds between rows

    header = ["timestamp", "temperature_c", "pressure_bar", "event"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write(",".join(header) + "\n")

    ambient_temp = 22.0
    ambient_pressure = 1.0
    temp = ambient_temp
    pressure = ambient_pressure
    row_count = 0
    start_time = time.time()

    temp_rise_per_min = 2.0  # °C per minute
    pressure_rise_per_min = 0.05  # bar per minute
    event_trigger_time = 10 * 60  # seconds (e.g., after 10 minutes, a reaction occurs)
    event_temp_spike = 20.0       # °C
    event_pressure_spike = 1.5    # bar
    event_duration = 3 * 60       # seconds (event lasts 3 minutes)

    print(f"Starting deterministic GrindControl data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec
            event = 0

            # Before event: temp/pressure rise linearly
            if elapsed < event_trigger_time:
                temp = ambient_temp + (temp_rise_per_min / 60) * elapsed
                pressure = ambient_pressure + (pressure_rise_per_min / 60) * elapsed
            # Event: sudden spike
            elif event_trigger_time <= elapsed < event_trigger_time + event_duration:
                temp = ambient_temp + (temp_rise_per_min / 60) * event_trigger_time + event_temp_spike
                pressure = ambient_pressure + (pressure_rise_per_min / 60) * event_trigger_time + event_pressure_spike
                event = 1
            # After event: temp/pressure plateau or cool down
            else:
                temp = ambient_temp + (temp_rise_per_min / 60) * event_trigger_time + event_temp_spike - 0.01 * (elapsed - event_trigger_time - event_duration)
                pressure = ambient_pressure + (pressure_rise_per_min / 60) * event_trigger_time + event_pressure_spike - 0.001 * (elapsed - event_trigger_time - event_duration)

            # Clamp to sensor range
            temp = max(TEMP_MIN, min(temp, TEMP_MAX))
            pressure = max(PRESSURE_MIN, min(pressure, PRESSURE_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "temperature_c": round(temp, 2),
                "pressure_bar": round(pressure, 3),
                "event": event
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)
            print(f"Wrote row {row_count+1}: Temp={temp:.2f}C, Pressure={pressure:.3f}bar, Event={event}")
            row_count += 1
            time.sleep(time_interval_sec)
    except KeyboardInterrupt:
        print("\nData generation stopped by user.")

# For standalone testing (remove if using only as a module)
if __name__ == "__main__":
    generate_retsch_grindcontrol_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\retsch_grindcontrol_data.csv"
    )
