import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import csv
import logging
from pathlib import Path
from math import cos, pi

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_realistic_inductive_data(
        output_file_path,
        sensor_id: str = "NBN40-U1-E2-V1",
        time_interval_seconds: float = 0.1,
        rated_operating_distance_mm: float = 40,
        hysteresis_percent: float = 0.05,
        switching_function: str = "NO",
        run_duration_seconds: int = None,
        conveyor_speed_mps: float = 0.5,
        object_spacing_m: float = 0.3,
        object_length_m: float = 0.1
):
    """
    Generates realistic inductive sensor data following conveyor belt patterns.
    All datasheet specifications preserved exactly as per Pepperl+Fuchs NBN40-U1-E2-V1.
    Runs infinitely if run_duration_seconds is None.
    """

    logger.info(f"Sensor [{sensor_id}]: Starting realistic pattern generation")
    if run_duration_seconds:
        logger.info(f"Sensor [{sensor_id}]: Will run for {run_duration_seconds} seconds")
    else:
        logger.info(f"Sensor [{sensor_id}]: Running infinitely until stopped")

    sim_start_time = datetime.now()

    # Calculate realistic timing patterns
    time_between_objects = object_spacing_m / conveyor_speed_mps
    object_detection_time = object_length_m / conveyor_speed_mps

    # VERIFIED datasheet hysteresis calculations
    hysteresis_mm = rated_operating_distance_mm * hysteresis_percent
    turn_on_distance = rated_operating_distance_mm
    turn_off_distance = rated_operating_distance_mm + hysteresis_mm

    # Pattern state tracking
    last_object_time = time.time()
    last_electrical_output_state = 1 if switching_function.upper() == "NC" else 0

    output_file_path = Path(output_file_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0

    with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)

        if not file_exists:
            csv_writer.writerow([
                "timestamp", "sensor_id", "distance_to_target_mm",
                "output_state", "switching_function"
            ])

        i = 0
        try:
            while True:
                # Check duration only if specified
                if run_duration_seconds and (datetime.now() - sim_start_time).total_seconds() > run_duration_seconds:
                    break

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                current_time = time.time()

                time_since_last_object = current_time - last_object_time
                time_in_cycle = time_since_last_object % time_between_objects

                # Define two realistic states
                object_detected_distance = 53  # mm
                no_object_distance = 58  # mm

                if time_in_cycle < object_detection_time:
                    distance_to_target = object_detected_distance + np.random.normal(0, 0.3)
                else:
                    distance_to_target = no_object_distance + np.random.normal(0, 0.3)

                distance_to_target = max(0, distance_to_target)

                # Apply VERIFIED hysteresis logic from datasheet
                previous_internal_sensing_state = 0
                if switching_function.upper() == "NO":
                    previous_internal_sensing_state = last_electrical_output_state
                elif switching_function.upper() == "NC":
                    previous_internal_sensing_state = 1 - last_electrical_output_state

                if previous_internal_sensing_state == 0:
                    internal_target_sensed_state = 1 if distance_to_target <= turn_on_distance else 0
                else:
                    internal_target_sensed_state = 0 if distance_to_target > turn_off_distance else 1

                # Apply VERIFIED NO/NC logic from datasheet
                if switching_function.upper() == "NO":
                    current_electrical_output_state = internal_target_sensed_state
                elif switching_function.upper() == "NC":
                    current_electrical_output_state = 1 - internal_target_sensed_state

                last_electrical_output_state = current_electrical_output_state

                csv_writer.writerow([
                    timestamp,
                    sensor_id,
                    round(distance_to_target, 2),
                    current_electrical_output_state,
                    switching_function.upper()
                ])

                i += 1
                if i % 1000 == 0:
                    logger.debug(f"Sensor [{sensor_id}]: Generated {i} points")

                time.sleep(time_interval_seconds)

        except KeyboardInterrupt:
            logger.info(f"Sensor [{sensor_id}]: Stopped by user interrupt")
        except Exception as e:
            logger.error(f"Sensor [{sensor_id}]: Error occurred: {e}")

    logger.info(f"Sensor [{sensor_id}]: Completed. Generated {i} data points.")


if __name__ == "__main__":
    # Run inductive sensor infinitely
    output_path = "../../data_output/conveyor_belt/inductive_NBN40-CB1-PRESENCE_data.csv"
    generate_realistic_inductive_data(output_path, run_duration_seconds=None)
