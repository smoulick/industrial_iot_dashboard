import threading
import logging
from pathlib import Path
import sys

# Configure Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Import sensor generators
from data_generators.conveyor_belt.inductive_sensor import generate_realistic_inductive_data
from data_generators.conveyor_belt.ultrasonic_sensor import generate_realistic_ultrasonic_data
from data_generators.conveyor_belt.heat_sensor import generate_realistic_heat_data
from data_generators.conveyor_belt.idler_roller.smart_idler_sensor import SmartIdlerSimulator
from data_generators.conveyor_belt.pulley.incremental_encoder import IncrementalEncoderSimulator
from data_generators.conveyor_belt.touchswitch_conveyor import generate_touchswitch_conveyor_data
from data_generators.conveyor_belt.pulley.touchswitch_pulley import generate_touchswitch_pulley_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MainDataGenerator:
    def __init__(self, base_output_path="data_output/conveyor_belt"):
        self.base_path = Path(base_output_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.threads = []

        self.sensor_configs = {
            "inductive": {
                "function": generate_realistic_inductive_data,
                "default_file": "inductive_NBN40-CB1-PRESENCE_data.csv",
                "description": "NBN40-U1-E2-V1 Inductive Proximity Sensor"
            },
            "ultrasonic": {
                "function": generate_realistic_ultrasonic_data,
                "default_file": "ultrasonic_UB800-CB1-MAIN_data.csv",
                "description": "UB800-18GM40-E5-V1 Ultrasonic Distance Sensor"
            },
            "heat": {
                "function": generate_realistic_heat_data,
                "default_file": "heat_PATOL5450-CB1-HOTSPOT_data.csv",
                "description": "PATOL5450 Heat Detection Sensor"
            },
            "smart_idler": {
                "function": SmartIdlerSimulator().generate_data,
                "default_file": "smart_idler_data.csv",
                "description": "Vayeron Smart-Idler Integrated Sensor"
            },
            "incremental_encoder": {
                "function": IncrementalEncoderSimulator().generate_data,
                "default_file": "incremental_encoder_data.csv",
                "description": "Hubner HOG 10 Incremental Encoder"
            },
            "touchswitch_conveyor": {
                "function": generate_touchswitch_conveyor_data,
                "default_file": "touchswitch_conveyor.csv",
                "description": "4B Touchswitch TS2V4AI Conveyor Belt Alignment Sensor"
            },
            "touchswitch_pulley": {
                "function": generate_touchswitch_pulley_data,
                "description": "4B Touchswitch TS2V4AI Pulley Alignment Sensor"
                # No default_file, no arguments needed!
            }
        }

    def run_all_sensors(self, duration_seconds=None):
        logger.info("=" * 80)
        logger.info("STARTING INDUSTRIAL IOT SENSOR SIMULATION")
        logger.info(f"Output Directory: {self.base_path}")
        logger.info("=" * 80)

        self.running = True
        self.threads = []

        for sensor_type, config in self.sensor_configs.items():
            sensor_kwargs = {}

            if sensor_type in ["smart_idler", "incremental_encoder"]:
                output_path = self.base_path / config["default_file"]
                sensor_kwargs["output_path"] = output_path
                if duration_seconds is not None and sensor_type == "smart_idler":
                    sensor_kwargs["duration_hours"] = duration_seconds / 3600

            elif sensor_type in ["inductive", "ultrasonic", "heat"]:
                output_path = self.base_path / config["default_file"]
                sensor_kwargs["output_file_path"] = output_path  # For these sensors
                if duration_seconds is not None:
                    sensor_kwargs["run_duration_seconds"] = duration_seconds

            elif sensor_type == "touchswitch_conveyor":
                output_path = self.base_path / config["default_file"]
                sensor_kwargs["output_path"] = output_path  # For conveyor Touchswitch
                if duration_seconds is not None:
                    sensor_kwargs["run_duration_seconds"] = duration_seconds

            # For touchswitch_pulley: no arguments needed!

            thread = threading.Thread(
                target=config["function"],
                kwargs=sensor_kwargs,
                name=f"{sensor_type}_thread",
                daemon=True
            )

            self.threads.append(thread)
            thread.start()
            logger.info(f"🚀 Started {config['description']}")

        try:
            for thread in self.threads:
                thread.join()

            logger.info("=" * 80)
            logger.info("✅ ALL SENSORS COMPLETED SUCCESSFULLY!")
            logger.info("📁 Generated files:")
            for sensor_type, config in self.sensor_configs.items():
                if "default_file" in config:
                    file_path = self.base_path / config["default_file"]
                    logger.info(f"   - {file_path}")
            logger.info("=" * 80)

        except KeyboardInterrupt:
            logger.info("🛑 Simulation interrupted by user")
            self.stop_all_sensors()

        self.running = False

    def stop_all_sensors(self):
        logger.info("🛑 Stopping all sensor simulations...")
        self.running = False
        for thread in self.threads:
            thread.join(timeout=5)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Industrial IoT Sensor Data Generator")
    parser.add_argument("--duration", type=int, help="Run duration in seconds")
    args = parser.parse_args()

    generator = MainDataGenerator()
    try:
        generator.run_all_sensors(duration_seconds=args.duration)
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
