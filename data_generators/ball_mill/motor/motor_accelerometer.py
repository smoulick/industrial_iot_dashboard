import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_motor_accelerometer_data_stream(output_path, run_duration_seconds=None):
    ACCEL_MIN, ACCEL_MAX = -10.0, 10.0  # g
    time_interval_sec = 10              # seconds between samples

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        df_init = pd.DataFrame(columns=["timestamp", "accel_x_g", "accel_y_g", "accel_z_g", "event"])
        df_init.to_csv(output_path, index=False)

    row_count = 0
    start_time = time.time()

    # Define realistic motor operation cycle
    idle_duration = 3 * 60
    ramp_up_duration = 2 * 60
    steady_state_duration = 8 * 60
    fault_duration = 2 * 60
    shutdown_duration = 2 * 60
    total_cycle = idle_duration + ramp_up_duration + steady_state_duration + fault_duration + shutdown_duration

    print(f"📡 Generating motor accelerometer data → {output_path} (Ctrl+C to stop)")

    try:
        while run_duration_seconds is None or (time.time() - start_time < run_duration_seconds):
            elapsed = (row_count * time_interval_sec) % total_cycle
            event = 0

            # Phase 1: Idle – low noise
            if elapsed < idle_duration:
                amp_x = 0.05
                amp_y = 0.03
                amp_z = 0.04

            # Phase 2: Ramp-up
            elif idle_duration <= elapsed < idle_duration + ramp_up_duration:
                factor = (elapsed - idle_duration) / ramp_up_duration
                amp_x = 0.1 + 1.5 * factor
                amp_y = 0.1 + 1.0 * factor
                amp_z = 0.1 + 0.8 * factor

            # Phase 3: Steady operation
            elif idle_duration + ramp_up_duration <= elapsed < idle_duration + ramp_up_duration + steady_state_duration:
                amp_x = 2.0
                amp_y = 1.5
                amp_z = 1.2

            # Phase 4: Fault (imbalance or bearing defect)
            elif idle_duration + ramp_up_duration + steady_state_duration <= elapsed < idle_duration + ramp_up_duration + steady_state_duration + fault_duration:
                amp_x = 6.0
                amp_y = 5.0
                amp_z = 4.5
                event = 1

            # Phase 5: Shutdown – decay
            else:
                t = elapsed - (idle_duration + ramp_up_duration + steady_state_duration + fault_duration)
                decay = 1.0 - (t / shutdown_duration)
                amp_x = 2.0 * decay
                amp_y = 1.5 * decay
                amp_z = 1.2 * decay

            # Base sinusoidal signal
            base_x = amp_x * math.sin(2 * math.pi * elapsed / 60)
            base_y = amp_y * math.sin(2 * math.pi * elapsed / 90 + math.pi / 4)
            base_z = amp_z * math.sin(2 * math.pi * elapsed / 120 + math.pi / 2)

            # Clamp values
            accel_x = max(ACCEL_MIN, min(base_x, ACCEL_MAX))
            accel_y = max(ACCEL_MIN, min(base_y, ACCEL_MAX))
            accel_z = max(ACCEL_MIN, min(base_z, ACCEL_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "accel_x_g": round(accel_x, 4),
                "accel_y_g": round(accel_y, 4),
                "accel_z_g": round(accel_z, 4),
                "event": event
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"📝 Row {row_count+1}: X={accel_x:.4f}g, Y={accel_y:.4f}g, Z={accel_z:.4f}g | Event={event}")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("⛔ Motor Accelerometer generation stopped.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_motor_accelerometer_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\motor_accelerometer_data.csv"
    )
