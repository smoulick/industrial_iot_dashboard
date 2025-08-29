import pandas as pd
from datetime import datetime
import os
import time
import math

def generate_mill_shell_acoustic_data_stream(output_path, run_duration_seconds=None):
    SOUND_MIN, SOUND_MAX = 50, 120      # dB
    FILL_MIN, FILL_MAX = 40, 130        # %
    time_interval_sec = 10              # 10 sec between samples

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(output_path):
        df_init = pd.DataFrame(columns=["timestamp", "sound_db", "fill_level_pct", "event"])
        df_init.to_csv(output_path, index=False)

    row_count = 0
    start_time = time.time()

    # Process phases (seconds)
    warmup = 4 * 60
    stable = 6 * 60
    event_start = 10 * 60
    event_end = event_start + 2 * 60
    cooldown = 15 * 60
    cycle_duration = cooldown + 2 * 60

    print(f"📡 Generating Mill Shell Acoustic data → {output_path} (Ctrl+C to stop)")

    try:
        while (run_duration_seconds is None) or (time.time() - start_time < run_duration_seconds):
            elapsed = (row_count * time_interval_sec) % cycle_duration
            event = 0

            # ---- Phase Logic ----
            if elapsed < warmup:
                # Fill slowly ramps from 45% to 70%
                fill_level = 45 + 25 * (elapsed / warmup)
                sound_db = 68 + 2 * math.sin(2 * math.pi * elapsed / 90)
            elif warmup <= elapsed < event_start:
                # Stable grinding phase
                t = elapsed - warmup
                fill_level = 70 + 3 * math.sin(2 * math.pi * t / 120)
                sound_db = 72 + 5 * math.sin(2 * math.pi * t / 90)
            elif event_start <= elapsed < event_end:
                # Event: surge in fill & sound
                t = elapsed - event_start
                fill_level = 100 + 20 * math.sin(math.pi * t / (event_end - event_start))
                sound_db = 90 + 15 * math.sin(math.pi * t / (event_end - event_start))
                event = 1
            else:
                # Cooldown and decay
                t = elapsed - event_end
                fill_level = 100 - 30 * (t / (cooldown - event_end))
                sound_db = 75 - 10 * (t / (cooldown - event_end))

            fill_level = max(FILL_MIN, min(fill_level, FILL_MAX))
            sound_db = max(SOUND_MIN, min(sound_db, SOUND_MAX))

            timestamp = datetime.now().isoformat()
            new_row = pd.DataFrame([{
                "timestamp": timestamp,
                "sound_db": round(sound_db, 2),
                "fill_level_pct": round(fill_level, 1),
                "event": event
            }])
            new_row.to_csv(output_path, mode='a', header=False, index=False)

            print(f"📝 Row {row_count+1}: Sound={sound_db:.2f} dB | Fill={fill_level:.1f}% | Event={event}")
            row_count += 1
            time.sleep(time_interval_sec)

    except KeyboardInterrupt:
        print("⛔ Acoustic data generation stopped.")

# For standalone testing (optional)
if __name__ == "__main__":
    generate_mill_shell_acoustic_data_stream(
        r"D:\Project\industrial_iot_dashboard\data_output\ball_mill\mill_shell_acoustic_data.csv"
    )
