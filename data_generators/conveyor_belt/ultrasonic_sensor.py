import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import csv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_realistic_ultrasonic_data(
        output_file_path,
        sensor_id: str = "UB800-18GM60-E5-V1-M",
        time_interval_seconds: float = 0.1,
        a1_threshold_mm: int = 200,  # Teachable near threshold
        a2_threshold_mm: int = 600,  # Teachable far threshold
        run_duration_seconds: int = None,
        production_cycle_minutes: float = 5.0,
        shift_hours: tuple = (6, 22)
):
    """
    Generates realistic switch-output ultrasonic sensor data.
    UB800-18GM60-E5-V1-M is a digital switch sensor - only HIGH/LOW output.
    No analog distance measurement available.
    """

    logger.info(f"Sensor [{sensor_id}]: Starting switch-output ultrasonic simulation")
    if run_duration_seconds:
        logger.info(f"Sensor [{sensor_id}]: Will run for {run_duration_seconds} seconds")
    else:
        logger.info(f"Sensor [{sensor_id}]: Running infinitely until stopped")

    sim_start_time = datetime.now()
    production_cycle_seconds = production_cycle_minutes * 60
    cycle_start_time = time.time()

    # State tracking for switch sensor
    switching_events = 0
    last_output_state = 0

    # Production patterns for object presence/absence
    production_patterns = [
        {"name": "high_throughput", "object_frequency": 0.7, "cycle_speed": 1.0},
        {"name": "medium_throughput", "object_frequency": 0.5, "cycle_speed": 0.8},
        {"name": "low_throughput", "object_frequency": 0.3, "cycle_speed": 0.6}
    ]
    current_pattern = 0

    output_file_path = Path(output_file_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0

    with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)

        if not file_exists:
            csv_writer.writerow([
                "timestamp", "sensor_id", "output_state",
                "switching_events", "uptime_seconds", "production_phase"
            ])

        i = 0
        try:
            while True:
                # Check duration only if specified
                if run_duration_seconds and (datetime.now() - sim_start_time).total_seconds() > run_duration_seconds:
                    break

                timestamp = datetime.now()
                current_hour = timestamp.hour
                uptime = (timestamp - sim_start_time).total_seconds()

                # Check if in production hours
                is_production_active = shift_hours[0] <= current_hour <= shift_hours[1]

                if not is_production_active:
                    # No production - no objects detected
                    current_output_state = 0
                    production_phase = "idle"
                else:
                    # Production cycle pattern
                    time_in_cycle = (time.time() - cycle_start_time) % production_cycle_seconds
                    cycle_progress = time_in_cycle / production_cycle_seconds

                    if cycle_progress < 0.1:
                        # Cycle start - loading, no objects yet
                        current_output_state = 0
                        production_phase = "loading"
                    elif cycle_progress < 0.8:
                        # Production active - objects moving through detection zone

                        # Change production pattern occasionally
                        if i % 500 == 0:
                            current_pattern = (current_pattern + 1) % len(production_patterns)

                        pattern = production_patterns[current_pattern]

                        # Simulate object presence based on pattern
                        object_cycle_time = 3.0 / pattern["cycle_speed"]  # Base 3-second object cycles
                        object_position = (uptime % object_cycle_time) / object_cycle_time

                        # Object detected when in the middle portion of cycle
                        object_detection_window = pattern["object_frequency"]
                        detection_start = (1.0 - object_detection_window) / 2
                        detection_end = detection_start + object_detection_window

                        if detection_start < object_position < detection_end:
                            current_output_state = 1  # Object detected in A1-A2 zone
                        else:
                            current_output_state = 0  # No object or outside detection zone

                        production_phase = f"production_{pattern['name']}"
                    else:
                        # Cycle end - unloading, sporadic objects
                        unload_cycle = (uptime % 2.0) / 2.0  # 2-second unload cycles
                        current_output_state = 1 if unload_cycle < 0.3 else 0  # 30% object presence
                        production_phase = "unloading"

                # Count switching events (important for switch sensors)
                if current_output_state != last_output_state:
                    switching_events += 1
                    logger.debug(
                        f"Sensor [{sensor_id}]: Output switched to {current_output_state} (Event #{switching_events})")

                last_output_state = current_output_state

                csv_writer.writerow([
                    timestamp.isoformat(),
                    sensor_id,
                    current_output_state,
                    switching_events,
                    round(uptime, 2),
                    production_phase
                ])

                i += 1
                if i % 1000 == 0:
                    logger.debug(f"Sensor [{sensor_id}]: Generated {i} points, {switching_events} switching events")

                time.sleep(time_interval_seconds)

        except KeyboardInterrupt:
            logger.info(f"Sensor [{sensor_id}]: Stopped by user interrupt")
        except Exception as e:
            logger.error(f"Sensor [{sensor_id}]: Error occurred: {e}")

    logger.info(f"Sensor [{sensor_id}]: Completed. Generated {i} data points, {switching_events} switching events.")


if __name__ == "__main__":
    # Run ultrasonic switch sensor infinitely
    output_path = "../../data_output/conveyor_belt/ultrasonic_UB800-CB1-MAIN_data.csv"
    generate_realistic_ultrasonic_data(output_path, run_duration_seconds=None)
