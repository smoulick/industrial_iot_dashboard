# D:\Project\industrial_iot_dashboard\data_generators\conveyor_belt\heat_sensor.py
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path
import time
import csv
import logging

logger = logging.getLogger(__name__)

# --- Parameters inspired by Datasheet Patol 5450 (not all directly simulatable) ---
# Application: Detection of hazards at temperatures below flame point, embers, buried hot spots [cite: 2]
# Sensitivity: 10 to 40 microWatt (4 levels) [cite: 2] -> Simplified to a temperature threshold for simulation
# Indicators: External Green Normal LED, Red Trip LED [cite: 2]
# Relay outputs: Volt free fire & fault relays [cite: 2]

DEFAULT_TIME_INTERVAL_SECONDS = 1.0  # Heat events might not need sub-second resolution as much
DEFAULT_AMBIENT_TEMP_CELSIUS = 25.0
DEFAULT_HOT_SPOT_TEMP_THRESHOLD_CELSIUS = 80.0  # Temp at which a "hot spot" is considered an alarm
DEFAULT_PROBABILITY_OF_HOT_SPOT = 0.01  # 1% chance per interval of a hot spot appearing
DEFAULT_PROBABILITY_OF_FAULT = 0.001  # 0.1% chance per interval of a sensor fault


def generate_heat_data(
        output_file_path: Path,
        sensor_id: str = "PATOL5450_sim",
        time_interval_seconds: float = DEFAULT_TIME_INTERVAL_SECONDS,
        ambient_temp_celsius: float = DEFAULT_AMBIENT_TEMP_CELSIUS,
        hot_spot_detection_threshold_celsius: float = DEFAULT_HOT_SPOT_TEMP_THRESHOLD_CELSIUS,
        probability_of_hot_spot: float = DEFAULT_PROBABILITY_OF_HOT_SPOT,
        hot_spot_max_temp_celsius: float = 200.0,  # Max temp a simulated hot spot can reach
        probability_of_fault: float = DEFAULT_PROBABILITY_OF_FAULT,
        run_duration_seconds: int = None
):
    """
    Generates synthetic data for a Patol 5450 Infra Red Transit Heat Sensor.
    Simulates detection of hot spots on a conveyor.
    """
    logger.info(f"Sensor [{sensor_id}]: Starting heat sensor data generation. Output: {output_file_path}")
    logger.info(
        f"Sensor [{sensor_id}]: AmbientTemp={ambient_temp_celsius}°C, HotSpotThreshold={hot_spot_detection_threshold_celsius}°C, Interval={time_interval_seconds}s")

    sim_start_time = datetime.now()

    # Sensor states
    fire_alarm_state = 0  # 0 = Normal, 1 = Fire/Trip Alarm
    fault_state = 0  # 0 = Normal, 1 = Fault
    # LED states based on alarm/fault
    green_led_normal = 1  # 1 = ON, 0 = OFF
    red_led_trip = 0  # 1 = ON, 0 = OFF

    # Simulated material temperature (fluctuates around ambient)
    current_material_temp = ambient_temp_celsius

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0

    i = 0
    with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        if not file_exists:
            csv_writer.writerow([
                "timestamp", "sensor_id", "simulated_material_temp_c",
                "fire_alarm_state", "fault_state",
                "green_led_normal_status", "red_led_trip_status"
            ])

        logger.info(f"Sensor [{sensor_id}]: Entering main data generation loop.")
        while True:
            if run_duration_seconds is not None and (
                    datetime.now() - sim_start_time).total_seconds() > run_duration_seconds:
                logger.info(f"Sensor [{sensor_id}]: Completed run duration of {run_duration_seconds} seconds.")
                break

            timestamp = datetime.now()

            # Simulate material temperature
            # Normally around ambient, with occasional hot spots
            if random.random() < probability_of_hot_spot:
                # Hot spot detected!
                current_material_temp = random.uniform(hot_spot_detection_threshold_celsius, hot_spot_max_temp_celsius)
                logger.warning(
                    f"Sensor [{sensor_id}]: Simulated HOT SPOT detected! Temp: {current_material_temp:.2f}°C")
            else:
                # Normal material temperature, fluctuating slightly around ambient
                current_material_temp = ambient_temp_celsius + np.random.normal(0, 2)  # Fluctuate +/- a few degrees
                current_material_temp = np.clip(current_material_temp, ambient_temp_celsius - 10,
                                                ambient_temp_celsius + 20)

            # Simulate random fault state (can be expanded with specific fault types)
            if random.random() < probability_of_fault:
                fault_state = 1 - fault_state  # Toggle fault state
                logger.warning(f"Sensor [{sensor_id}]: Simulated FAULT state changed to: {fault_state}")

            # Determine alarm state based on material temperature
            if current_material_temp >= hot_spot_detection_threshold_celsius:
                fire_alarm_state = 1
            else:
                fire_alarm_state = 0  # Reset if below threshold (assuming no latching unless explicitly modeled)

            # Determine LED states based on datasheet [cite: 2]
            # External: Green Normal LED. Red Trip LED.
            if fault_state == 1:
                green_led_normal = 0  # Assuming fault overrides normal indication
                red_led_trip = 0  # Or Red could flash for fault - datasheet says "Volt free fire & fault relays"
                # and "Red Trip LED" for fire. Let's assume Red Trip is only for fire.
                # For simplicity, fault means Green OFF.
            elif fire_alarm_state == 1:
                green_led_normal = 0
                red_led_trip = 1
            else:  # Normal operation
                green_led_normal = 1
                red_led_trip = 0

            csv_writer.writerow([
                timestamp.isoformat(),
                sensor_id,
                round(current_material_temp, 2),
                fire_alarm_state,
                fault_state,
                green_led_normal,
                red_led_trip
            ])

            i += 1
            if i > 0 and i % 60 == 0:  # Log progress every 60 points (e.g. every minute at 1s interval)
                logger.debug(
                    f"Sensor [{sensor_id}]: Generated {i} data points. Material Temp: {current_material_temp:.2f}°C, Alarm: {fire_alarm_state}, Fault: {fault_state}")

            try:
                time.sleep(time_interval_seconds)
            except KeyboardInterrupt:
                logger.info(f"Sensor [{sensor_id}]: Keyboard interrupt. Stopping generation.")
                break

        logger.info(f"Sensor [{sensor_id}]: Exited main data generation loop.")

    logger.info(f"Sensor [{sensor_id}]: Heat sensor data generation process finished.")


if __name__ == "__main__":
    project_root_for_test = Path(__file__).resolve().parent.parent.parent
    test_output_dir = project_root_for_test / "data_output" / "conveyor_belt" / "_test_heat_standalone"
    test_output_dir.mkdir(parents=True, exist_ok=True)

    if not logging.getLogger().hasHandlers():  # Ensure basicConfig is only called if no handlers exist
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    test_sensor_id = "PATOL5450-TEST-01"
    test_params = {
        "output_file_path": test_output_dir / f"test_{test_sensor_id}.csv",
        "sensor_id": test_sensor_id,
        "time_interval_seconds": 0.5,  # Faster for testing
        "ambient_temp_celsius": 30.0,
        "hot_spot_detection_threshold_celsius": 75.0,
        "probability_of_hot_spot": 0.05,  # More frequent hot spots for testing
        "hot_spot_max_temp_celsius": 150.0,
        "probability_of_fault": 0.01,  # More frequent faults for testing
        "run_duration_seconds": 30  # Short run for test
    }

    print(f"--- Running Standalone Test for Heat Sensor ---")
    try:
        generate_heat_data(**test_params)
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback

        traceback.print_exc()
    print(f"--- Test Finished. Data: {test_params['output_file_path']} ---")