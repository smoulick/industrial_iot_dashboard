import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

def generate_tr10b_temperature_stream(output_path, run_duration_seconds=None):
    TEMP_MIN, TEMP_MAX = -196, 600  # °C, as per datasheet
    time_interval_sec = 30  # seconds between rows

    header = ["timestamp", "temperature_c", "event"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write(",".join(header) + "\n")

    ambient_temp = 25.0  # °C
    temp = ambient_temp
    row_count = 0
    start_time = time.time()

    # Simulation parameters
    temp_rise_per_min = 5.0  # °C per minute
    event_trigger_time = 15 * 60  # seconds: after 15 min
    event_temp_spike = 80.0       # °C spike during event
    event_duration = 5 * 60       # seconds (5 minutes)
    post_event_cool_rate = 0.05   # °C/sec

    print(f"Starting TR10-B temperature data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec
            event = 0

            # Normal heating phase
            if elapsed < event_trigger_time:
                temp = ambient_temp + (temp_rise_per_min / 60) * elapsed
            # Event phase
            elif event_trigger_time <= elapsed < event_trigger_time + event_duration:
                base_temp = ambient_temp + (temp_rise_per_min / 60) * event_trigger_time
                temp = base_temp + event_temp_spike
                event = 1
            # Cooling phase after event
            else:
                base_temp = ambient_temp + (temp_rise_per_min / 60) * event_trigger_time + event_temp_spike
                temp = base_temp - post_event_cool_rate * (elapsed - event_trigger_time - event_duration)

            # Add realistic sensor accuracy noise (± 0.1 + 0.0017*|t| for Class AA)
            noise_std = 0.1 + 0.0017 * abs(temp)
            temp += np.random.normal(0, noise_std)

            # Clamp to sensor range
            temp = max(TEMP_MIN, min(temp, TEMP_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "temperature_c": round(temp, 2),
                "event": event
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)
            print(f"Wrote row {row_count+1}: Temp={temp:.2f} °C, Event={event}")
            row_count += 1
            time.sleep(time_interval_sec)
    except KeyboardInterrupt:
        print("\nTR10-B data generation stopped by user.")

# For standalone testing
if __name__ == "__main__":
    generate_tr10b_temperature_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\tr10b_temperature.csv"
    )
