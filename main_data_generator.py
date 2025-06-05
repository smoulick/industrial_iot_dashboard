from datetime import datetime
import logging
from pathlib import Path
import threading
import argparse
import sys
import signal

# Import from your structure
try:
    from data_generators.conveyor_belt.inductive_sensor import generate_realistic_inductive_data
    from data_generators.conveyor_belt.ultrasonic_sensor import generate_realistic_ultrasonic_data
    from data_generators.conveyor_belt.heat_sensor import generate_realistic_heat_data
except ImportError as error:
    print(f"Error importing sensor modules: {error}")
    print("Make sure sensor files are in data_generators/conveyor_belt/ directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sensor_simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MainDataGenerator:
    """Main data generator with infinite runtime capability."""

    def __init__(self, base_output_path="data_output/conveyor_belt"):
        self.base_path = Path(base_output_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.threads = []

        # Sensor configs with BOTH PRESENCE and LIMIT inductive sensors
        self.sensor_configs = {
            "inductive_presence": {
                "function": generate_realistic_inductive_data,
                "default_file": "inductive_NBN40-CB1-PRESENCE_data.csv",
                "description": "NBN40-U1-E2-V1 Inductive Proximity Sensor (Presence Detection)",
                "sensor_id": "NBN40-CB1-PRESENCE"
            },
            "inductive_limit": {
                "function": generate_realistic_inductive_data,
                "default_file": "inductive_NBN40-CB1-LIMIT_data.csv",
                "description": "NBN40-U1-E2-V1 Inductive Proximity Sensor (Limit Switch)",
                "sensor_id": "NBN40-CB1-LIMIT"
            },
            "ultrasonic": {
                "function": generate_realistic_ultrasonic_data,
                "default_file": "ultrasonic_UB800-CB1-MAIN_data.csv",
                "description": "UB800-18GM40-E5-V1 Ultrasonic Distance Sensor",
                "sensor_id": "UB800-CB1-MAIN"
            },
            "heat": {
                "function": generate_realistic_heat_data,
                "default_file": "heat_PATOL5450-CB1-HOTSPOT_data.csv",
                "description": "PATOL5450 Heat Detection Sensor",
                "sensor_id": "PATOL5450-CB1-HOTSPOT"
            }
        }

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        logger.info("🛑 Received interrupt signal. Stopping all sensors...")
        self.stop_all_sensors()
        sys.exit(0)

    def run_all_sensors(self, duration_seconds=None):
        """Run all sensors. If duration_seconds is None, runs infinitely."""

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)

        logger.info("=" * 80)
        logger.info("STARTING CONVEYOR BELT SENSOR SIMULATION")
        logger.info(f"Output Directory: {self.base_path}")
        if duration_seconds:
            logger.info(f"Duration: {duration_seconds} seconds")
        else:
            logger.info("Duration: INFINITE (until Ctrl+C)")
        logger.info("=" * 80)

        self.running = True
        self.threads = []

        for sensor_type, config in self.sensor_configs.items():
            output_path = self.base_path / config["default_file"]

            # Prepare parameters
            params = {
                "output_file_path": output_path,
                "run_duration_seconds": duration_seconds,  # None for infinite
                "sensor_id": config["sensor_id"]
            }

            thread = threading.Thread(
                target=config["function"],
                kwargs=params,
                name=f"{sensor_type}_thread",
                daemon=True  # Daemon threads will exit when main program exits
            )

            self.threads.append(thread)
            thread.start()
            logger.info(f"🚀 Started {sensor_type} sensor ({config['sensor_id']})")

        try:
            if duration_seconds:
                # Wait for specified duration
                for thread in self.threads:
                    thread.join()
            else:
                # Run infinitely - keep main thread alive
                logger.info("✅ All sensors started. Running infinitely...")
                logger.info("Press Ctrl+C to stop all sensors")
                while self.running:
                    # Check if any thread died unexpectedly
                    alive_threads = [t for t in self.threads if t.is_alive()]
                    if len(alive_threads) != len(self.threads):
                        logger.warning(
                            f"Some sensor threads stopped unexpectedly. Alive: {len(alive_threads)}/{len(self.threads)}")

                    # Sleep and check again
                    import time
                    time.sleep(10)

            logger.info("=" * 80)
            logger.info("✅ ALL CONVEYOR BELT SENSORS COMPLETED!")
            logger.info("📁 Generated files:")
            for sensor_type, config in self.sensor_configs.items():
                file_path = self.base_path / config["default_file"]
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    logger.info(f"   - {file_path} ({size_mb:.2f} MB)")
            logger.info("=" * 80)

        except KeyboardInterrupt:
            logger.info("🛑 Simulation interrupted by user")
            self.stop_all_sensors()
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            self.stop_all_sensors()

        self.running = False

    def stop_all_sensors(self):
        """Stop all running sensor simulations."""
        logger.info("🛑 Stopping all sensor simulations...")
        self.running = False

        # Threads will stop naturally due to the interrupt handling in each sensor
        logger.info("🛑 All sensors will stop gracefully")


def main():
    """Main function with infinite runtime support."""
    parser = argparse.ArgumentParser(
        description="Conveyor Belt Sensor Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run infinitely until Ctrl+C
  python main_data_generator.py

  # Run infinitely (explicit)
  python main_data_generator.py --infinite

  # Run for specific duration
  python main_data_generator.py --duration 3600  # 1 hour
        """
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in seconds (default: infinite)"
    )
    parser.add_argument(
        "--infinite",
        action="store_true",
        help="Run infinitely until stopped (default behavior)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data_output/conveyor_belt",
        help="Output directory for data files"
    )

    args = parser.parse_args()

    # Determine duration
    if args.infinite:
        duration = None
    else:
        duration = args.duration  # None by default, so infinite

    logger.info("🏭 Industrial IoT Sensor Data Generator")
    logger.info("=" * 50)

    generator = MainDataGenerator(base_output_path=args.output_dir)
    generator.run_all_sensors(duration_seconds=duration)


if __name__ == "__main__":
    main()
