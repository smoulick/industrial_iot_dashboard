import numpy as np
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_touchswitch_conveyor_data(
    output_path="data_output/conveyor_belt/touchswitch_conveyor.csv",
    sensor_id="TS2V4AI-CONV-001"
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0

    thermal_fuse_blown = False
    last_alarm_start = None
    in_alarm = False
    thermal_alarm_threshold = timedelta(minutes=5)
    production_hours = (6, 22)

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

                # Simulate force (no false alarms from dust/material)
                if operational_mode:
                    force = np.random.uniform(1.0, 4.0)
                    if np.random.rand() < 0.05:
                        force = np.random.uniform(8.5, 15.0)
                else:
                    force = np.random.uniform(0.5, 2.0)

                # Alarm and thermal fuse logic
                alignment_status = 1 if force >= 8.0 else 0
                if alignment_status == 1 and not in_alarm:
                    last_alarm_start = now
                    in_alarm = True
                elif alignment_status == 0:
                    last_alarm_start = None
                    in_alarm = False

                if in_alarm and last_alarm_start:
                    if now - last_alarm_start >= thermal_alarm_threshold:
                        thermal_fuse_blown = True

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
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Touchswitch conveyor simulation stopped")
