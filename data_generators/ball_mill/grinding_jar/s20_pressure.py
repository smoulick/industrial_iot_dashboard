import pandas as pd
from datetime import datetime
import numpy as np
import time
import os

def generate_s20_pressure_stream(output_path, run_duration_seconds=None):
    PRESSURE_MIN, PRESSURE_MAX = 0, 1600  # bar
    time_interval_sec = 30  # seconds between samples

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        with open(output_path, "w") as f:
            f.write("timestamp,pressure_bar,event\n")

    row_count = 0
    start_time = time.time()

    # Behavior parameters
    ambient = 1.0              # bar
    nominal = 40.0            # bar
    ramp_time = 5 * 60        # ramp-up to nominal
    stable_time = 10 * 60     # flat running
    spike_time = 3 * 60       # pressure event (e.g. valve block)
    cool_time = 7 * 60        # decay phase
    total_cycle = ramp_time + stable_time + spike_time + cool_time

    print(f"📡 Generating S-20 pressure data → {output_path} (Ctrl+C to stop)")

    try:
        while run_duration_seconds is None or (time.time() - start_time) < run_duration_seconds:
            elapsed = (row_count * time_interval_sec) % total_cycle
            event = 0

            if elapsed < ramp_time:
                # Linear ramp from ambient to nominal
                pressure = ambient + (nominal - ambient) * (elapsed / ramp_time)

            elif ramp_time <= elapsed < ramp_time + stable_time:
                # Slight sinusoidal variation
                t = elapsed - ramp_time
                pressure = nominal + 1.0 * np.sin(2 * np.pi * t / 60)  # 1-min cycles

            elif ramp_time + stable_time <= elapsed < ramp_time + stable_time + spike_time:
                # Simulated overpressure event
                t = elapsed - ramp_time - stable_time
                pressure = 250 + 80 * np.sin(np.pi * t / spike_time)  # smooth sinusoidal bump
                event = 1

            else:
                # Cooling decay
                t = elapsed - ramp_time - stable_time - spike_time
                pressure = 250 * np.exp(-0.05 * t)

            pressure = max(PRESSURE_MIN, min(pressure, PRESSURE_MAX))

            timestamp = datetime.now().isoformat()
            row = f"{timestamp},{round(pressure, 2)},{event}\n"
            with open(output_path, "a") as f:
                f.write(row)

            print(f"[{timestamp}] Pressure: {pressure:.2f} bar | Event: {event}")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("⛔ S-20 pressure data generation stopped.")

if __name__ == "__main__":
    generate_s20_pressure_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\s20_pressure_data.csv"
    )
