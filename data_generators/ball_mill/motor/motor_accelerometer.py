import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_motor_accelerometer_data_stream(output_path, run_duration_seconds=None):
    # Sensor parameters (based on real specs)
    ACCEL_MIN, ACCEL_MAX = -10.0, 10.0  # g, typical industrial range for motors
    time_interval_sec = 10               # seconds between samples

    # Prepare output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        df_init = pd.DataFrame(columns=["timestamp", "accel_x_g", "accel_y_g", "accel_z_g"])
        df_init.to_csv(output_path, index=False)

    row_count = 0
    start_time = time.time()

    # Deterministic process parameters
    # Simulate periodic motor vibration, with a deterministic "fault" event (spike)
    event_trigger_time = 12 * 60      # seconds (event at 12 min)
    event_duration = 2 * 60           # seconds (event lasts 2 min)
    event_spike = 5.0                 # g spike in all axes

    print(f"Starting deterministic Motor Accelerometer data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec

            # Simulate base vibration (sinusoidal, different phase for each axis)
            base_x = 2.0 * math.sin(2 * math.pi * (elapsed / 60))
            base_y = 1.5 * math.sin(2 * math.pi * (elapsed / 90) + math.pi/4)
            base_z = 1.0 * math.sin(2 * math.pi * (elapsed / 120) + math.pi/2)

            # Event: sudden spike in all axes
            if event_trigger_time <= elapsed < event_trigger_time + event_duration:
                accel_x = base_x + event_spike
                accel_y = base_y + event_spike
                accel_z = base_z + event_spike
            else:
                accel_x, accel_y, accel_z = base_x, base_y, base_z

            # Clamp to sensor range
            accel_x = max(ACCEL_MIN, min(accel_x, ACCEL_MAX))
            accel_y = max(ACCEL_MIN, min(accel_y, ACCEL_MAX))
            accel_z = max(ACCEL_MIN, min(accel_z, ACCEL_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "accel_x_g": round(accel_x, 4),
                "accel_y_g": round(accel_y, 4),
                "accel_z_g": round(accel_z, 4)
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"Wrote row {row_count+1}: X={accel_x:.4f}g, Y={accel_y:.4f}g, Z={accel_z:.4f}g")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("\nMotor Accelerometer data generation stopped by user.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_motor_accelerometer_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\motor_accelerometer_data.csv"
    )
