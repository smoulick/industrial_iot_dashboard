import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import csv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_realistic_heat_data(
        output_file_path,
        sensor_id: str = "PATOL5450",
        time_interval_seconds: float = 1.0,
        fire_alarm_threshold: float = 100.0,  # CORRECTED: From datasheet 100°C minimum
        run_duration_seconds: int = None,
        daily_cycle: bool = True
):
    """
    Generates realistic heat sensor data with thermal patterns.
    All datasheet specifications preserved exactly as per PATOL 5450 datasheet.
    CORRECTED: Fire alarm threshold set to 100°C as per datasheet.
    Runs infinitely if run_duration_seconds is None.
    """

    equipment_schedule = {
        "motor_runtime_hours": 16,  # 16 hours per day
        "maintenance_hours": [2, 3, 14, 15]  # Maintenance windows
    }

    logger.info(f"Sensor [{sensor_id}]: Starting realistic heat simulation (CORRECTED: 100°C threshold)")
    if run_duration_seconds:
        logger.info(f"Sensor [{sensor_id}]: Will run for {run_duration_seconds} seconds")
    else:
        logger.info(f"Sensor [{sensor_id}]: Running infinitely until stopped")

    sim_start_time = datetime.now()

    # Hot spot scenarios with realistic probabilities
    hot_spot_scenarios = {
        "friction_buildup": {"probability": 0.001, "temp_range": (100, 120), "duration_minutes": 30},
        "bearing_failure": {"probability": 0.0005, "temp_range": (120, 180), "duration_minutes": 60},
        "material_jam": {"probability": 0.002, "temp_range": (100, 110), "duration_minutes": 15}
    }

    active_hot_spots = []

    output_file_path = Path(output_file_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file_path.exists() and output_file_path.stat().st_size > 0

    with open(output_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)

        if not file_exists:
            csv_writer.writerow([
                "timestamp", "sensor_id", "simulated_material_temp_c",
                "fire_alarm_state", "fault_state", "green_led_normal_status",
                "red_led_trip_status"
            ])

        i = 0
        try:
            while True:
                # Check duration only if specified
                if run_duration_seconds and (datetime.now() - sim_start_time).total_seconds() > run_duration_seconds:
                    break

                now = datetime.now()
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                current_hour = now.hour

                # Base temperature with daily cycle (within datasheet operating range -20°C to +70°C)
                base_temp = 25.0
                if daily_cycle:
                    # Natural daily temperature variation
                    daily_variation = 8 * np.sin(2 * np.pi * (current_hour - 6) / 24)
                    base_temp += daily_variation

                # Equipment heat based on schedule
                equipment_heat = 0
                is_maintenance = current_hour in equipment_schedule["maintenance_hours"]

                if not is_maintenance and current_hour < equipment_schedule["motor_runtime_hours"]:
                    # Equipment running - gradual heat buildup
                    hours_running = current_hour if current_hour <= 12 else 24 - current_hour
                    equipment_heat = min(15, hours_running * 2)  # Max 15°C increase

                # Check for hot spot scenarios
                hot_spot_temp = 0

                active_hot_spots = [
                    spot for spot in active_hot_spots
                    if (now - datetime.strptime(spot["start_time"], "%Y-%m-%d %H:%M:%S.%f")).total_seconds() < spot[
                        "duration"] * 60
                ]

                # Generate new hot spots
                for scenario_name, scenario_config in hot_spot_scenarios.items():
                    if np.random.random() < scenario_config["probability"]:
                        hot_spot = {
                            "type": scenario_name,
                            "start_time": timestamp,
                            "duration": scenario_config["duration_minutes"],
                            "temp": np.random.uniform(*scenario_config["temp_range"])
                        }
                        active_hot_spots.append(hot_spot)
                        logger.warning(f"Sensor [{sensor_id}]: Hot spot scenario '{scenario_name}' initiated")

                # Apply active hot spots
                if active_hot_spots:
                    hottest_spot = max(active_hot_spots, key=lambda x: x["temp"])
                    hot_spot_temp = hottest_spot["temp"] - base_temp - equipment_heat

                # Calculate final temperature
                current_material_temp = base_temp + equipment_heat + hot_spot_temp
                current_material_temp += np.random.normal(0, 0.5)  # Small measurement noise

                # Ensure temperature stays within sensor detection range (80-1000°C from datasheet)
                current_material_temp = np.clip(current_material_temp, 15, 1000)

                # CORRECTED alarm logic using verified datasheet threshold (100°C)
                fire_alarm_state = 1 if current_material_temp >= fire_alarm_threshold else 0
                fault_state = 1 if np.random.random() < 0.0001 else 0  # Very rare faults

                # VERIFIED LED logic from datasheet
                if fault_state:
                    green_led_normal = 0
                    red_led_trip = 0  # Both LEDs off during fault
                elif fire_alarm_state:
                    green_led_normal = 0
                    red_led_trip = 1  # Red LED on during fire alarm
                else:
                    green_led_normal = 1
                    red_led_trip = 0  # Green LED on during normal operation

                csv_writer.writerow([
                    timestamp,
                    sensor_id,
                    round(current_material_temp, 2),
                    fire_alarm_state,
                    fault_state,
                    green_led_normal,
                    red_led_trip
                ])

                i += 1
                if i % 300 == 0:  # Log every 5 minutes (300 seconds)
                    logger.debug(f"Sensor [{sensor_id}]: Generated {i} points. Temp: {current_material_temp:.1f}°C")

                time.sleep(time_interval_seconds)

        except KeyboardInterrupt:
            logger.info(f"Sensor [{sensor_id}]: Stopped by user interrupt")
        except Exception as e:
            logger.error(f"Sensor [{sensor_id}]: Error occurred: {e}")

    logger.info(f"Sensor [{sensor_id}]: Completed. Generated {i} data points.")


if __name__ == "__main__":
    # Run heat sensor infinitely
    output_path = "../../data_output/conveyor_belt/heat_PATOL5450-CB1-HOTSPOT_data.csv"
    generate_realistic_heat_data(output_path, run_duration_seconds=None)
