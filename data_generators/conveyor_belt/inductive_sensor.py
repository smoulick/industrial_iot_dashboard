# D:\Project\industrial_iot_dashboard\data_generators\conveyor_belt\inductive_sensor.py
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path
import time
import csv
import logging

logger = logging.getLogger(__name__)

# --- Parameters derived from Datasheet NBN40-U1L-Z2 (233001_eng.pdf) ---
DATASHEET_RATED_OPERATING_DISTANCE_SN = 40  # mm
DATASHEET_HYSTERESIS_TYPICAL_PERCENT = 0.05  # typ. 5% of Sr/Sn
DEFAULT_TIME_INTERVAL_SECONDS = 0.02


def generate_inductive_data(
        output_file_path: Path,
        sensor_id: str = "NBN40_sim",
        time_interval_seconds: float = DEFAULT_TIME_INTERVAL_SECONDS,
        rated_operating_distance_mm: float = DATASHEET_RATED_OPERATING_DISTANCE_SN,
        hysteresis_percent: float = DATASHEET_HYSTERESIS_TYPICAL_PERCENT,
        switching_function: str = "NO",  # "NO" (Normally Open) or "NC" (Normally Closed)
        run_duration_seconds: int = None
):
    """
    Generates synthetic inductive sensor data mimicking NBN40-U1L-Z2.
    Assumes a standard ferrous target.
    """
    logger.info(f"Sensor [{sensor_id}]: Starting inductive data generation. Output: {output_file_path}")
    logger.info(
        f"Sensor [{sensor_id}]: RatedDistance={rated_operating_distance_mm}mm, Hysteresis={hysteresis_percent * 100}%, SwitchFunc='{switching_function}', Interval={time_interval_seconds}s")

    sim_start_time = datetime.now()

    # Initialize last_output_state based on switching_function
    # For NO: output 0 means not detecting. If object is initially not present, sensor output is 0.
    # For NC: output 1 means not detecting. If object is initially not present, sensor output is 1.
    if switching_function.upper() == "NC":
        # This 'last_output_state' represents the actual electrical output of the sensor.
        # If NC and no object, output is ON (1).
        last_electrical_output_state = 1
    else:  # Default to NO
        # If NO and no object, output is OFF (0).
        last_electrical_output_state = 0

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0

    hysteresis_mm = rated_operating_distance_mm * hysteresis_percent
    turn_on_distance = rated_operating_distance_mm  # Object detected when distance <= this
    turn_off_distance = rated_operating_distance_mm + hysteresis_mm  # Object no longer detected when distance > this

    i = 0
    with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        if not file_exists:
            csv_writer.writerow(
                ["timestamp", "sensor_id", "distance_to_target_mm", "output_state", "switching_function"])

        logger.info(f"Sensor [{sensor_id}]: Entering main data generation loop.")
        while True:
            if run_duration_seconds is not None and (
                    datetime.now() - sim_start_time).total_seconds() > run_duration_seconds:
                logger.info(f"Sensor [{sensor_id}]: Completed run duration of {run_duration_seconds} seconds.")
                break

            timestamp = datetime.now()

            cycle_time_seconds = 10
            current_cycle_pos = (time.time() % cycle_time_seconds) / cycle_time_seconds

            sim_max_dist = turn_off_distance + 10
            sim_min_dist = 0

            if current_cycle_pos < 0.5:
                distance_to_target = sim_max_dist - (current_cycle_pos * 2 * sim_max_dist)
            else:
                distance_to_target = (current_cycle_pos - 0.5) * 2 * sim_max_dist

            distance_to_target = np.clip(distance_to_target, sim_min_dist, sim_max_dist)
            distance_to_target += np.random.normal(0, 0.1)
            distance_to_target = max(0, distance_to_target)

            # Determine internal detection state (1 if target is sensed, 0 if not)
            # This is before considering NO/NC characteristic for the *electrical output*
            internal_target_sensed_state = 0

            # 'last_electrical_output_state' reflects the previous actual output.
            # We need to determine the raw sensing state based on physics.
            # Let's track if the sensor *would* be 'ON' in a raw sense (target present).
            # This logic is based on typical hysteresis:
            # If currently not sensing a target: it starts sensing if distance <= turn_on_distance.
            # If currently sensing a target: it stops sensing if distance > turn_off_distance.

            # To simplify, let's determine if the sensor *should be* internally "active" (target present)
            # This part of the logic was a bit tangled. Let's refine it:

            # Assume 'is_currently_sensing_target' is true if the target was within turn_off_distance on the last cycle,
            # and becomes false if it moves beyond turn_off_distance.
            # It becomes true if it was false and moves within turn_on_distance.

            # Let's use the 'last_electrical_output_state' to infer the previous *internal sensing state*
            previous_internal_sensing_state = 0
            if switching_function.upper() == "NO":
                previous_internal_sensing_state = last_electrical_output_state  # If NO, output = internal sense
            elif switching_function.upper() == "NC":
                previous_internal_sensing_state = 1 - last_electrical_output_state  # If NC, output = inverted internal sense

            if previous_internal_sensing_state == 0:  # Was not sensing target
                if distance_to_target <= turn_on_distance:
                    internal_target_sensed_state = 1
                else:
                    internal_target_sensed_state = 0
            else:  # Was sensing target (previous_internal_sensing_state == 1)
                if distance_to_target > turn_off_distance:
                    internal_target_sensed_state = 0
                else:
                    internal_target_sensed_state = 1

            # Apply NO/NC logic to the internal sensed state to get the electrical output
            current_electrical_output_state = 0
            if switching_function.upper() == "NO":
                current_electrical_output_state = internal_target_sensed_state
            elif switching_function.upper() == "NC":
                current_electrical_output_state = 1 - internal_target_sensed_state

            last_electrical_output_state = current_electrical_output_state

            csv_writer.writerow([
                timestamp.isoformat(),
                sensor_id,
                round(distance_to_target, 2),
                current_electrical_output_state,
                switching_function.upper()
            ])

            i += 1
            if i > 0 and i % 200 == 0:
                logger.debug(
                    f"Sensor [{sensor_id}]: Generated {i} data points. Current distance: {distance_to_target:.2f}mm, Output: {current_electrical_output_state}")

            try:
                time.sleep(time_interval_seconds)
            except KeyboardInterrupt:
                logger.info(f"Sensor [{sensor_id}]: Keyboard interrupt. Stopping generation.")
                break

        logger.info(f"Sensor [{sensor_id}]: Exited main data generation loop.")
    logger.info(f"Sensor [{sensor_id}]: Inductive data generation process finished.")


if __name__ == "__main__":
    project_root_for_test = Path(__file__).resolve().parent.parent.parent
    test_output_dir = project_root_for_test / "data_output" / "conveyor_belt" / "_test_inductive_standalone"
    test_output_dir.mkdir(parents=True, exist_ok=True)

    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    test_sensor_id_no = "NBN40-TEST-NO"
    test_params_no = {
        "output_file_path": test_output_dir / f"test_{test_sensor_id_no}.csv",
        "sensor_id": test_sensor_id_no,
        "time_interval_seconds": 0.05,
        "switching_function": "NO",
        "run_duration_seconds": 15
    }

    test_sensor_id_nc = "NBN40-TEST-NC"
    test_params_nc = {
        "output_file_path": test_output_dir / f"test_{test_sensor_id_nc}.csv",
        "sensor_id": test_sensor_id_nc,
        "time_interval_seconds": 0.05,
        "switching_function": "NC",
        "run_duration_seconds": 15
    }

    print(f"--- Running Standalone Test for Inductive Sensor (NO) ---")
    try:
        generate_inductive_data(**test_params_no)
    except Exception as e:
        print(f"Error during NO test: {e}")
        import traceback

        traceback.print_exc()
    print(f"--- Test (NO) Finished. Data: {test_params_no['output_file_path']} ---")

    print(f"\n--- Running Standalone Test for Inductive Sensor (NC) ---")
    try:
        generate_inductive_data(**test_params_nc)
    except Exception as e:
        print(f"Error during NC test: {e}")
        import traceback

        traceback.print_exc()
    print(f"--- Test (NC) Finished. Data: {test_params_nc['output_file_path']} ---")