import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_motor_temperature_data_stream(output_path, run_duration_seconds=None):
    # Sensor parameters (based on RTD/thermocouple specs)
    TEMP_MIN, TEMP_MAX = -40, 150  # °C, typical for industrial motors
    time_interval_sec = 10         # seconds between samples

    # Ensure header row
    header = ["timestamp", "temperature_c"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write(",".join(header) + "\n")

    row_count = 0
    start_time = time.time()

    # Deterministic process parameters
    # Normal operation: slow rise, with deterministic overheat event
    event_trigger_time = 15 * 60      # seconds (event at 15 min)
    event_duration = 2 * 60           # seconds (event lasts 2 min)
    event_temp_spike = 40.0           # °C spike

    print(f"Starting deterministic Motor Temperature data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec

            # Base temperature: ambient + slow rise
            base_temp = 35 + 0.03 * elapsed  # e.g., 35°C start, rises 0.03°C/sec

            # Event: overheat
            if event_trigger_time <= elapsed < event_trigger_time + event_duration:
                temperature = base_temp + event_temp_spike
            elif elapsed >= event_trigger_time + event_duration:
                # After event: plateau or slow cool
                temperature = max(base_temp + event_temp_spike - 0.01 * (elapsed - event_trigger_time - event_duration), base_temp)
            else:
                temperature = base_temp

            temperature = max(TEMP_MIN, min(temperature, TEMP_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "temperature_c": round(temperature, 2)
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"Wrote row {row_count+1}: Temperature={temperature:.2f}C")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("\nMotor Temperature data generation stopped by user.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_motor_temperature_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\motor_temperature_data.csv"
    )
