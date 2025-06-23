import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_mill_shell_vibration_data_stream(output_path, run_duration_seconds=None):
    # Sensor parameters
    VIBRATION_MIN, VIBRATION_MAX = 0.0, 10.0  # g (acceleration)
    TEMP_MIN, TEMP_MAX = 20, 90               # degrees Celsius
    time_interval_sec = 10                    # seconds between data points

    header = ["timestamp", "vibration_g", "temperature_c"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write(",".join(header) + "\n")

    row_count = 0
    start_time = time.time()

    # Deterministic process parameters
    event_trigger_time = 5 * 60      # seconds (event at 5 min)
    event_duration = 2 * 60          # seconds (event lasts 2 min)
    event_vibration_spike = 5.0      # g
    event_temp_spike = 10.0          # °C

    print(f"Starting deterministic Mill Shell Vibration data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec
            # Vibration: base periodic + deterministic event
            base_vibration = 2.0 + 1.5 * (1 + math.sin(2 * math.pi * (elapsed / 60) / 1))  # 1-min period

            # Event: sudden spike in vibration and temp
            if event_trigger_time <= elapsed < event_trigger_time + event_duration:
                vibration = base_vibration + event_vibration_spike
                temperature = 30 + 0.02 * elapsed + event_temp_spike
            # After event: vibration and temp return to normal/plateau
            elif elapsed >= event_trigger_time + event_duration:
                vibration = base_vibration
                temperature = min(60, 30 + 0.02 * event_trigger_time + event_temp_spike + 0.005 * (elapsed - event_trigger_time - event_duration))
            # Before event: normal operation
            else:
                vibration = base_vibration
                temperature = 30 + 0.02 * elapsed

            vibration = max(VIBRATION_MIN, min(vibration, VIBRATION_MAX))
            temperature = max(TEMP_MIN, min(temperature, TEMP_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "vibration_g": round(vibration, 3),
                "temperature_c": round(temperature, 2)
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"Wrote row {row_count+1}: Vibration={vibration:.3f}g, Temperature={temperature:.2f}C")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("\nMill Shell Vibration data generation stopped by user.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_mill_shell_vibration_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\mill_shell_vibration_data.csv"
    )
