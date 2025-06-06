import numpy as np
import time
import csv
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartIdlerSimulator:
    def __init__(self, sensor_id="SI-OFBA-6309-45-40-03"):
        self.sensor_id = sensor_id
        self.sampling_interval = 0.1  # 10 Hz for summary data (vibration sampled at 1399 Hz internally)
        self.last_defect_time = time.time()
        self.rotation_count = 0
        self.bearing_defects = {
            'BPFI': False,  # Inner race defect
            'BPFO': False,  # Outer race defect
            'BSF': False,   # Ball spin defect
            'FTF': False    # Cage defect
        }
        self.operational_limits = {
            'temp_range': (-20, 150),
            'rpm_range': (350, 1500),
            'vibration_mode1_range': (-2, 2),
            'vibration_mode2_range': (-16, 16),
            'alert_thresholds': {
                'temp': 80,         # °C
                'vibration_rms': 1.5, # g
                'rpm_deviation': 15  # %
            }
        }

    def calculate_rpm(self, belt_speed_mps=0.5, idler_diameter_mm=159):
        """Calculate RPM based on belt speed and idler diameter"""
        circumference = np.pi * idler_diameter_mm / 1000  # meters
        expected_rpm = (belt_speed_mps * 60) / circumference
        actual_rpm = expected_rpm * np.random.uniform(0.95, 1.05)
        return np.clip(actual_rpm, *self.operational_limits['rpm_range']), expected_rpm

    def generate_vibration_data(self, rpm, defect_type=None):
        """Simulate vibration spectra with potential defects"""
        base_vibration = {
            'rms': np.random.uniform(0.1, 0.5),
            'BPFI': np.random.uniform(0.01, 0.1),
            'BPFO': np.random.uniform(0.01, 0.1),
            'BSF': np.random.uniform(0.01, 0.1),
            'FTF': np.random.uniform(0.01, 0.1)
        }
        # Simulate defects
        if defect_type in self.bearing_defects and self.bearing_defects[defect_type]:
            base_vibration[defect_type] *= np.random.uniform(5, 10)
            base_vibration['rms'] = np.clip(base_vibration['rms'] * 3, *self.operational_limits['vibration_mode1_range'])
        return base_vibration

    def check_alerts(self, temp_left, temp_right, vibration_rms, actual_rpm, expected_rpm):
        """Generate alerts based on datasheet thresholds"""
        alerts = []
        # Temperature alerts
        if temp_left > self.operational_limits['alert_thresholds']['temp']:
            alerts.append("TEMP_LEFT_HIGH")
        if temp_right > self.operational_limits['alert_thresholds']['temp']:
            alerts.append("TEMP_RIGHT_HIGH")
        # Vibration alerts
        if vibration_rms > self.operational_limits['alert_thresholds']['vibration_rms']:
            alerts.append("VIBRATION_HIGH")
        # RPM deviation
        rpm_deviation = abs((actual_rpm - expected_rpm)/expected_rpm)*100
        if rpm_deviation > self.operational_limits['alert_thresholds']['rpm_deviation']:
            alerts.append("RPM_DEVIATION")
        return alerts

    def generate_data(self, output_path, duration_hours=None):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Writing Smart-Idler data to: {output_path.resolve()}")
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "timestamp", "sensor_id", "rotation_count", "rpm",
                "temp_left", "temp_right", "vibration_rms",
                "BPFI", "BPFO", "BSF", "FTF", "alerts"
            ])
            start_time = time.time()
            while True:
                if duration_hours and (time.time() - start_time) > duration_hours*3600:
                    break
                timestamp = datetime.now().isoformat()
                actual_rpm, expected_rpm = self.calculate_rpm()
                self.rotation_count += int(actual_rpm * self.sampling_interval / 60)
                # Simulate temperatures (left/right bearings)
                temp_left = np.random.normal(35, 2)
                temp_right = np.random.normal(35, 2)
                temp_left += (actual_rpm - 350) * 0.01
                temp_right += (actual_rpm - 350) * 0.01
                temp_left = np.clip(temp_left, *self.operational_limits['temp_range'])
                temp_right = np.clip(temp_right, *self.operational_limits['temp_range'])
                # Simulate vibration, possibly with a defect
                defect_type = None
                if any(self.bearing_defects.values()):
                    defect_type = np.random.choice([k for k, v in self.bearing_defects.items() if v])
                vibration = self.generate_vibration_data(actual_rpm, defect_type)
                # Check for alerts
                alerts = self.check_alerts(temp_left, temp_right, vibration['rms'], actual_rpm, expected_rpm)
                writer.writerow([
                    timestamp, self.sensor_id, self.rotation_count,
                    round(actual_rpm, 1),
                    round(temp_left, 1), round(temp_right, 1),
                    round(vibration['rms'], 4),
                    round(vibration['BPFI'], 4),
                    round(vibration['BPFO'], 4),
                    round(vibration['BSF'], 4),
                    round(vibration['FTF'], 4),
                    ";".join(alerts) if alerts else "NORMAL"
                ])
                # Simulate a new defect every hour
                if time.time() - self.last_defect_time > 3600:
                    defect = np.random.choice(list(self.bearing_defects.keys())+[None], p=[0.02,0.02,0.02,0.02,0.92])
                    if defect:
                        self.bearing_defects[defect] = True
                        self.last_defect_time = time.time()
                        logger.warning(f"Simulating {defect} defect on {self.sensor_id}")
                time.sleep(self.sampling_interval)

if __name__ == "__main__":
    simulator = SmartIdlerSimulator()
    try:
        logger.info("Starting Vayeron Smart-Idler® simulation")
        # Always resolve output file from project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        output_file = project_root / "data_output" / "conveyor_belt" / "smart_idler_data.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing to: {output_file.resolve()}")
        simulator.generate_data(output_file)
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    except Exception as e:
        logger.error(f"Simulation error: {e}")
