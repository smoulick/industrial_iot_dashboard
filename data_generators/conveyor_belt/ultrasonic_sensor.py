# In D:\Project\industrial_iot_dashboard\data_generators\conveyor_belt\ultrasonic_sensor.py
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path
import time
from collections import deque
import csv
import logging

# Get a logger for this module. Configuration will be handled by the main script.
logger = logging.getLogger(__name__)  # Will be named 'data_generators.conveyor_belt.ultrasonic_sensor'

# --- Parameters derived from Datasheet UB800-18GM60-E5-V1-M ---
# General specifications
DATASHEET_SENSING_RANGE_MIN = 50  # mm, from "Sensing range" 50...800mm and "Dead band" 0...50mm [cite: 1]
DATASHEET_SENSING_RANGE_MAX = 800  # mm, from "Sensing range" 50...800mm [cite: 1]
DATASHEET_ADJUSTMENT_RANGE_MIN = 70  # mm (Default A1 for simulation) [cite: 1]
DATASHEET_ADJUSTMENT_RANGE_MAX = 800  # mm (Default A2 for simulation) [cite: 1]
DATASHEET_RESPONSE_DELAY_MS = 100  # ms, approx. [cite: 1]

# Output specifications
DATASHEET_DEFAULT_A1 = 70  # mm, from "Default setting" [cite: 5]
DATASHEET_DEFAULT_A2 = 800  # mm, from "Default setting" [cite: 5]
DATASHEET_REPEAT_ACCURACY_PERCENT = 0.01  # <= 1% (as a fraction for calculation) [cite: 5]
DATASHEET_RANGE_HYSTERESIS_PERCENT = 0.01  # 1% of the set operating distance (as a fraction) [cite: 5]

# Temperature influence: +/- 1.5% of full-scale value [cite: 5]
FSV_FOR_TEMP_EFFECT = DATASHEET_SENSING_RANGE_MAX - DATASHEET_SENSING_RANGE_MIN  # 750mm (800mm - 50mm)
OPERATING_TEMP_SPAN_C = 70 - (-25)  # 95°C (from Ambient temperature -25 ... 70°C) [cite: 5]
DATASHEET_TEMP_INFLUENCE_TOTAL_PERCENT = 0.015  # 1.5% as a fraction [cite: 5]
# Calculated effective drift percentage of FSV per degree Celsius for simulation:
DATASHEET_TEMP_INFLUENCE_PERCENT_PER_C = DATASHEET_TEMP_INFLUENCE_TOTAL_PERCENT / OPERATING_TEMP_SPAN_C # approx 0.00015789...ox 0.00015789...

# Ambient conditions
DATASHEET_AMBIENT_TEMP_MIN = -25  # °C [cite: 5]
DATASHEET_AMBIENT_TEMP_MAX = 70  # °C [cite: 5]

# Other defaults for simulation
DEFAULT_MODES = [1, 2, 3, 4, 5]
DEFAULT_TIME_INTERVAL_SECONDS = 0.05


def generate_ultrasonic_data(
        output_file_path: Path,
        sensor_id: str = "UB800_sim",
        time_interval_seconds: float = DEFAULT_TIME_INTERVAL_SECONDS,
        a1: int = DATASHEET_DEFAULT_A1,
        a2: int = DATASHEET_DEFAULT_A2,
        response_delay_ms: int = DATASHEET_RESPONSE_DELAY_MS,
        modes: list = None,
        run_duration_seconds: int = None
):
    """
    Generates synthetic ultrasonic sensor data mimicking Pepperl+Fuchs UB800-18GM60-E5-V1-M
    and saves it to a CSV file.
    """
    if modes is None:
        modes = DEFAULT_MODES[:]

    log_extra = {'sensor_id': sensor_id}  # Context for logging, needs specific handler/formatter to use sensor_id tag

    # These initial logs will use the formatter from main_data_generator.py
    # To include sensor_id here directly in the message if not using complex logging:
    logger.info(f"Sensor [{sensor_id}]: Starting data generation. Output: {output_file_path}")
    logger.info(
        f"Sensor [{sensor_id}]: Datasheet-based params: A1_default={DATASHEET_DEFAULT_A1}mm, A2_default={DATASHEET_DEFAULT_A2}mm, ResponseDelay={response_delay_ms}ms")
    logger.info(
        f"Sensor [{sensor_id}]: Simulation settings: a1_set={a1}mm, a2_set={a2}mm, interval={time_interval_seconds}s, modes={modes}")

    try:
        logger.info(f"Sensor [{sensor_id}]: STAGE 1: Initializing variables")
        sim_start_time = datetime.now()

        base_distance_calc = (a1 + a2) / 2
        distance_range_for_noise_calc = min(abs(a2 - a1), (DATASHEET_SENSING_RANGE_MAX - DATASHEET_SENSING_RANGE_MIN))

        last_output = 0
        current_temp = 25.0  # Initial temperature, reference for temp influence

        logger.info(f"Sensor [{sensor_id}]: STAGE 2: Initializing deque buffer")
        if time_interval_seconds <= 0:
            logger.error(
                f"Sensor [{sensor_id}]: time_interval_seconds is zero or negative ({time_interval_seconds}), which is invalid. Aborting sensor task.")
            return

        buffer_size = max(1, int(response_delay_ms / (time_interval_seconds * 1000)))
        delay_buffer = deque(maxlen=buffer_size)
        logger.info(f"Sensor [{sensor_id}]: Buffer size calculated: {buffer_size}")

        i = 0
        mode_index = 0

        logger.info(f"Sensor [{sensor_id}]: STAGE 3: Preparing file path and checking existence")
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0
        logger.info(f"Sensor [{sensor_id}]: File path: {output_file_path}, Exists and not empty: {file_exists}")

        logger.info(f"Sensor [{sensor_id}]: STAGE 4: Attempting to open file for writing: {output_file_path}")
        with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            if not file_exists:
                csv_writer.writerow(["timestamp", "sensor_id", "distance_mm", "output", "temperature_C", "mode"])

            logger.info(f"Sensor [{sensor_id}]: STAGE 5: Entering main data generation loop.")
            while True:
                if run_duration_seconds is not None:
                    elapsed_time = (datetime.now() - sim_start_time).total_seconds()
                    if elapsed_time > run_duration_seconds:
                        logger.info(f"Sensor [{sensor_id}]: Completed run duration of {run_duration_seconds} seconds.")
                        break

                current_mode = modes[mode_index]
                timestamp = datetime.now()

                true_object_distance = random.uniform(DATASHEET_SENSING_RANGE_MIN, DATASHEET_SENSING_RANGE_MAX)
                raw_distance_mm = true_object_distance + np.random.normal(0, distance_range_for_noise_calc / 20)

                if random.random() < 0.02:
                    raw_distance_mm += random.uniform(-distance_range_for_noise_calc / 5,
                                                      distance_range_for_noise_calc / 5)

                accuracy_effect = np.random.uniform(-DATASHEET_REPEAT_ACCURACY_PERCENT,
                                                    DATASHEET_REPEAT_ACCURACY_PERCENT) * raw_distance_mm
                distance_with_accuracy_effect = raw_distance_mm + accuracy_effect

                distance_clipped_to_sensor_range = np.clip(distance_with_accuracy_effect, DATASHEET_SENSING_RANGE_MIN,
                                                           DATASHEET_SENSING_RANGE_MAX)

                current_temp += np.random.normal(0, 0.1)
                current_temp = np.clip(current_temp, DATASHEET_AMBIENT_TEMP_MIN, DATASHEET_AMBIENT_TEMP_MAX)

                temp_deviation_from_ref = current_temp - 25.0
                temp_drift_effect_mm = temp_deviation_from_ref * (
                            DATASHEET_TEMP_INFLUENCE_PERCENT_PER_C * FSV_FOR_TEMP_EFFECT)

                distance_with_temp_effect = distance_clipped_to_sensor_range + temp_drift_effect_mm
                distance_final_raw = np.clip(distance_with_temp_effect, DATASHEET_SENSING_RANGE_MIN,
                                             DATASHEET_SENSING_RANGE_MAX)

                delay_buffer.append(distance_final_raw)
                if len(delay_buffer) == delay_buffer.maxlen:
                    delayed_distance = delay_buffer[0]
                else:
                    delayed_distance = delay_buffer[-1]

                hyst_abs_a1 = DATASHEET_RANGE_HYSTERESIS_PERCENT * a1
                hyst_abs_a2 = DATASHEET_RANGE_HYSTERESIS_PERCENT * a2
                output = 0

                if current_mode == 1:
                    if last_output == 0:
                        if a1 <= delayed_distance <= a2: output = 1
                    else:
                        if not (a1 - hyst_abs_a1 <= delayed_distance <= a2 + hyst_abs_a2):
                            output = 0
                        else:
                            output = 1
                elif current_mode == 2:
                    if last_output == 1:
                        if a1 <= delayed_distance <= a2: output = 0
                    else:
                        if not (a1 - hyst_abs_a1 <= delayed_distance <= a2 + hyst_abs_a2):
                            output = 1
                        else:
                            output = 0
                elif current_mode == 3:
                    if last_output == 0:
                        if delayed_distance <= a2: output = 1
                    else:
                        if delayed_distance > a2 + hyst_abs_a2:
                            output = 0
                        else:
                            output = 1
                elif current_mode == 4:
                    if last_output == 0:
                        if delayed_distance >= a1: output = 1
                    else:
                        if delayed_distance < a1 - hyst_abs_a1:
                            output = 0
                        else:
                            output = 1
                elif current_mode == 5:
                    if delayed_distance <= a2:
                        output = 1
                    else:
                        output = 0

                last_output = output

                csv_writer.writerow([
                    timestamp.isoformat(), sensor_id, round(delayed_distance, 2),
                    output, round(current_temp, 2), current_mode
                ])

                i += 1
                if i > 0 and i % 100 == 0:
                    mode_index = (mode_index + 1) % len(modes)
                    # For debug logging, sensor_id is manually prepended.
                    logger.debug(
                        f"Sensor [{sensor_id}]: Generated {i} data points. Switched to mode {modes[mode_index]} for next cycle.")

                try:
                    time.sleep(time_interval_seconds)
                except KeyboardInterrupt:
                    logger.info(
                        f"Sensor [{sensor_id}]: Keyboard interrupt received during sleep. Stopping data generation.")
                    break

            logger.info(f"Sensor [{sensor_id}]: Exited main data generation loop.")

    except Exception as e:
        # Manually prepend sensor_id for clarity as log_extra might not be applied by root logger's default format
        logger.error(f"Sensor [{sensor_id}]: CRITICAL ERROR in generate_ultrasonic_data: {e}", exc_info=True)
        # This will print the traceback to see where the error occurred
        # The function will implicitly return None here if an exception occurs.

    logger.info(f"Sensor [{sensor_id}]: Data generation process finished or aborted due to error.")


if __name__ == "__main__":
    # This section is for testing this script standalone.
    project_root_for_test = Path(__file__).resolve().parent.parent.parent
    test_output_dir = project_root_for_test / "data_output" / "conveyor_belt" / "_test_datasheet_standalone_runs"
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Configure a temporary basicConfig for standalone testing if main isn't running it
    # This will only apply if this script is the entry point.
    if not logging.getLogger().hasHandlers():  # Check if root logger is already configured
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(name)s - SENSOR_ID_PLACEHOLDER - %(message)s')

    # For standalone test, sensor_id is passed directly
    test_sensor_id = "US-STANDALONE-DATASHEET-001"

    test_sensor_params = {
        "output_file_path": test_output_dir / f"test_{test_sensor_id}.csv",
        "sensor_id": test_sensor_id,
        "a1": DATASHEET_DEFAULT_A1,
        "a2": DATASHEET_DEFAULT_A2,
        "time_interval_seconds": 0.05,
        "response_delay_ms": DATASHEET_RESPONSE_DELAY_MS,
        "run_duration_seconds": 10,  # Short duration for test
        "modes": [1, 3, 5]
    }

    print(f"--- Running Standalone Test for Datasheet-based Ultrasonic Sensor ---")
    print(f"Sensor ID: {test_sensor_params['sensor_id']}")
    print(f"Outputting to: {test_sensor_params['output_file_path']}")
    print(f"Running for {test_sensor_params['run_duration_seconds']} seconds...")

    try:
        generate_ultrasonic_data(**test_sensor_params)
    except KeyboardInterrupt:
        print(f"\nStandalone test for {test_sensor_params['sensor_id']} stopped by user.")
    except Exception as e:
        print(f"An error occurred during standalone test: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print(f"--- Standalone Test Finished ---")
        print(f"Data (if any) saved to: {test_sensor_params['output_file_path']}")