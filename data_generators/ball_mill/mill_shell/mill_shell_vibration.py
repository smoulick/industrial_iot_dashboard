import pandas as pd
from datetime import datetime
import os
import time
import math
import random

def generate_mill_shell_vibration_data_stream(output_path, run_duration_seconds=None):
    # Sensor limits from datasheet
    VIBRATION_MIN, VIBRATION_MAX = -50.0, 50.0   # g
    TEMP_MIN, TEMP_MAX = 2.0, 121.0              # °C
    time_interval_sec = 10                       # Interval between readings

    header = ["timestamp", "vibration_g", "temperature_c"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write(",".join(header) + "\n")

    row_count = 0
    start_time = time.time()

    # Event simulation (e.g., fault or overload)
    event_trigger_time = 5 * 60           # 5 minutes
    event_duration = 2 * 60               # 2 minutes
    event_vibration_spike = 15.0          # g, added on top
    event_temp_spike = 15.0               # °C, added

    print(f"Streaming Mill Shell Vibration Data to {output_path} (Press Ctrl+C to stop)\n")

    try:
        while run_duration_seconds is None or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec

            # Periodic base vibration (simulate rotating machinery)
            base_vibration = 10.0 * math.sin(2 * math.pi * (elapsed / 60) / 2) + random.uniform(-1, 1)

            # Temperature baseline with slow rise
            base_temperature = 30.0 + 0.01 * elapsed + random.uniform(-0.5, 0.5)

            # During event: vibration + spike, temperature + spike
            if event_trigger_time <= elapsed < event_trigger_time + event_duration:
                vibration = base_vibration + event_vibration_spike
                temperature = base_temperature + event_temp_spike
            elif elapsed >= event_trigger_time + event_duration:
                # Cooldown after event
                vibration = base_vibration
                temperature = base_temperature + event_temp_spike * math.exp(-0.01 * (elapsed - event_trigger_time - event_duration))
            else:
                vibration = base_vibration
                temperature = base_temperature

            # Clamp to sensor limits
            vibration = max(VIBRATION_MIN, min(vibration, VIBRATION_MAX))
            temperature = max(TEMP_MIN, min(temperature, TEMP_MAX))

            # Write to CSV
            timestamp = datetime.now().isoformat()
            row = pd.DataFrame([{
                "timestamp": timestamp,
                "vibration_g": round(vibration, 3),
                "temperature_c": round(temperature, 2)
            }])
            row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"[{timestamp}] Vibration: {vibration:.3f}g | Temp: {temperature:.2f}°C")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("\nStopped by user.")

# Standalone run
if __name__ == "__main__":
    generate_mill_shell_vibration_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\mill_shell_vibration_data.csv"
    )
