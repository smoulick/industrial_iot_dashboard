# data_generators/conveyor_belt/pulley/incremental_encoder.py
import time
import csv
import logging
import numpy as np
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IncrementalEncoderSimulator:
    def __init__(self, sensor_id="INC-ENC-001"):
        self.sensor_id = sensor_id
        self.ppr = 1024  # Pulses Per Revolution
        self.sampling_interval = 0.01  # 100 Hz sampling
        self.pulse_count = 0
        self.direction = 1  # 1=forward, -1=reverse
        self.status = "NORMAL"

        # From HOG10 datasheet specs
        self.operational_limits = {
            'max_rpm': 6000,
            'voltage_range': (9, 30),
            'shock_resistance': 1000,  # m/s²
            'vibration_resistance': 300  # m/s²
        }

    def generate_pulses(self, rpm):
        """Simulate encoder output based on RPM"""
        pulses_per_second = (rpm / 60) * self.ppr
        return int(pulses_per_second * self.sampling_interval)

    def check_status(self, rpm):
        """Simulate encoder status monitoring"""
        if rpm > self.operational_limits['max_rpm']:
            return "OVERSPEED"
        if np.random.rand() < 0.002:  # 0.2% chance of random error
            return "SIGNAL_ERROR"
        return "NORMAL"

    def generate_data(self, output_path, duration_hours=None):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "timestamp", "sensor_id", "rpm",
                "pulse_count", "direction", "status"
            ])

            start_time = time.time()
            while True:
                if duration_hours and (time.time() - start_time) > duration_hours * 3600:
                    break

                # Simulate RPM with random variations
                base_rpm = 400  # Normal operating RPM
                rpm = base_rpm * np.random.uniform(0.98, 1.02)
                rpm = np.clip(rpm, 0, self.operational_limits['max_rpm'])

                # Generate pulses and direction
                new_pulses = self.generate_pulses(rpm)
                self.pulse_count += new_pulses * self.direction
                self.direction = 1 if np.random.rand() > 0.01 else -1  # 1% chance to reverse

                # Update status
                self.status = self.check_status(rpm)

                writer.writerow([
                    datetime.now().isoformat(),
                    self.sensor_id,
                    round(rpm, 1),
                    self.pulse_count,
                    "FORWARD" if self.direction == 1 else "REVERSE",
                    self.status
                ])

                time.sleep(self.sampling_interval)


if __name__ == "__main__":
    encoder = IncrementalEncoderSimulator()
    try:
        logger.info("Starting incremental encoder simulation")
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        output_file = project_root / "data_output" / "conveyor_belt" / "incremental_encoder_data.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        encoder.generate_data(output_file)
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    except Exception as e:
        logger.error(f"Encoder error: {e}")
