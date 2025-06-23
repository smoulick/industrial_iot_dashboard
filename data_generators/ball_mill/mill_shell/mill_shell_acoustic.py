import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_mill_shell_acoustic_data_stream(output_path, run_duration_seconds=None):
    # Sensor parameters (based on SmartFill, Pyrotech, etc.)
    SOUND_MIN, SOUND_MAX = 50, 120  # dB, typical industrial range
    FILL_MIN, FILL_MAX = 0, 130     # % of calibrated range (SmartFill)
    time_interval_sec = 10          # seconds between data points

    # Prepare output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        df_init = pd.DataFrame(columns=["timestamp", "sound_db", "fill_level_pct"])
        df_init.to_csv(output_path, index=False)

    row_count = 0
    start_time = time.time()

    # Deterministic process parameters
    event_trigger_time = 8 * 60      # seconds (event at 8 min)
    event_duration = 2 * 60          # seconds (event lasts 2 min)
    event_sound_spike = 20           # dB
    event_fill_spike = 30            # %

    print(f"Starting deterministic Mill Shell Acoustic data generation to {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = row_count * time_interval_sec
            # Sound: periodic base (simulates rotation/filling) + deterministic event
            base_sound = 70 + 10 * math.sin(2 * math.pi * (elapsed / 120))  # 2-min period
            base_fill = 60 + 20 * math.sin(2 * math.pi * (elapsed / 180))   # 3-min period

            # Event: sudden spike in sound and fill
            if event_trigger_time <= elapsed < event_trigger_time + event_duration:
                sound_db = base_sound + event_sound_spike
                fill_level = base_fill + event_fill_spike
            elif elapsed >= event_trigger_time + event_duration:
                sound_db = base_sound
                fill_level = max(FILL_MIN, min(base_fill, FILL_MAX))
            else:
                sound_db = base_sound
                fill_level = base_fill

            sound_db = max(SOUND_MIN, min(sound_db, SOUND_MAX))
            fill_level = max(FILL_MIN, min(fill_level, FILL_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "sound_db": round(sound_db, 2),
                "fill_level_pct": round(fill_level, 1)
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"Wrote row {row_count+1}: Sound={sound_db:.2f} dB, Fill={fill_level:.1f}%")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("\nMill Shell Acoustic data generation stopped by user.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_mill_shell_acoustic_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\mill_shell_acoustic_data.csv"
    )
