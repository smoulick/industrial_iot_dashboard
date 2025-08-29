import numpy as np
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_touchswitch_pulley_data(
    sensor_id="TS2V4AI-PULLEY-001"
):
    project_root = Path(__file__).resolve().parents[3]
    output_path = project_root / "data_output/conveyor_belt/touchswitch_pulley.csv"
    print("Writing to:", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0

    thermal_fuse_blown = False
    last_alarm_start = None
    in_alarm = False
    thermal_alarm_threshold = timedelta(minutes=5)
    production_hours = (6, 22)

    t = 0
    dt = 1  # 1 second interval

    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "timestamp", "sensor_id", "alignment_status",
                "relay_status", "led_status", "thermal_fuse_blown",
                "alerts", "measured_force", "operational_mode"
            ])
        try:
            while True:
                now = datetime.now()
                hour = now.hour
                operational_mode = 1 if production_hours[0] <= hour <= production_hours[1] else 0

                # 🎯 More realistic force pattern: sinusoid + noise
                base_force = 5 + 3 * np.sin(2 * np.pi * t / 300)  # 5-minute cycle
                noise = np.random.normal(0, 1)
                force = max(0, base_force + noise)  # prevent negative force

                # Occasional spikes to simulate heavy misalignment
                if operational_mode and np.random.rand() < 0.01:
                    force += np.random.uniform(5, 10)

                # Force is reduced when idle
                if not operational_mode:
                    force *= np.random.uniform(0.2, 0.5)

                # Alignment condition
                alignment_status = 1 if force >= 8.0 else 0

                # Track misalignment duration for thermal fuse
                if alignment_status == 1 and not in_alarm:
                    last_alarm_start = now
                    in_alarm = True
                elif alignment_status == 0:
                    last_alarm_start = None
                    in_alarm = False

                if in_alarm and last_alarm_start:
                    if now - last_alarm_start >= thermal_alarm_threshold:
                        thermal_fuse_blown = True

                # Alerts and indicators
                if thermal_fuse_blown:
                    relay_status = 0
                    led_status = 0
                    alerts = "THERMAL FUSE BLOWN"
                elif alignment_status == 1:
                    relay_status = 0
                    led_status = 0
                    alerts = "MISALIGNMENT"
                else:
                    relay_status = 1
                    led_status = 1
                    alerts = "NORMAL"

                # Log the row
                writer.writerow([
                    now.isoformat(),
                    sensor_id,
                    alignment_status,
                    relay_status,
                    led_status,
                    int(thermal_fuse_blown),
                    alerts,
                    round(force, 2),
                    operational_mode
                ])

                t += dt
                time.sleep(dt)
        except KeyboardInterrupt:
            logger.info("Touchswitch pulley simulation stopped")

if __name__ == "__main__":
    generate_touchswitch_pulley_data()
