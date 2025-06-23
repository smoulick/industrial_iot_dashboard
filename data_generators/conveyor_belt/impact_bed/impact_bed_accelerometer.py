import numpy as np
import time
import csv
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_impact_bed_accelerometer_data(
    sensor_id="ADXL1001-IMPACTBED-001",
    g_range=100,  # ±100g for ADXL1001, ±50g for ADXL1002
    sensitivity_mV_per_g=20,  # ADXL1001: 20 mV/g at 5V
    base_freq_hz=50,  # Typical conveyor vibration frequency
    sample_rate_hz=100,  # 100 Hz for dashboard demo (real sensor can go much higher)
):
    project_root = Path(__file__).resolve().parents[3]  # [3] for .../data_generators/conveyor_belt/pulley/
    output_path = project_root / "data_output/conveyor_belt/impact_bed_accelerometer.csv"
    print("Writing to:", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0

    # Vibration pattern: base sine + harmonics + low noise
    t = 0
    dt = 1.0 / sample_rate_hz
    impact_duration = 0.04  # seconds
    impact_samples = int(impact_duration * sample_rate_hz)
    impact_cooldown = 0

    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "timestamp", "sensor_id", "accel_x_g",
                "vibration_rms_g", "impact_peak_g", "impact_event",
                "overrange", "alerts"
            ])
        try:
            while True:
                # Simulate base vibration: 50 Hz sine + 150 Hz harmonic + low noise
                base = 2.0 * np.sin(2 * np.pi * base_freq_hz * t)
                harmonic = 0.5 * np.sin(2 * np.pi * 3 * base_freq_hz * t)
                noise = np.random.normal(0, 0.05)
                accel_x = base + harmonic + noise

                # Impact event: sharp, high-g spike
                if impact_cooldown == 0 and np.random.rand() < 0.01:
                    impact_profile = np.hanning(impact_samples) * np.random.uniform(20, 60)
                    impact_cooldown = impact_samples
                    impact_idx = 0
                if impact_cooldown > 0:
                    accel_x += impact_profile[impact_idx]
                    impact_idx += 1
                    impact_cooldown -= 1
                    impact_event = 1
                    impact_peak = impact_profile.max()
                else:
                    impact_event = 0
                    impact_peak = 0

                # Overrange detection (ADXL1001: ±100g)
                overrange = int(abs(accel_x) > g_range)
                vibration_rms = np.sqrt(accel_x ** 2)

                # Alerts
                if overrange:
                    alerts = "OVERRANGE"
                elif impact_event:
                    alerts = "IMPACT DETECTED"
                elif vibration_rms > 10:
                    alerts = "HIGH VIBRATION"
                else:
                    alerts = "NORMAL"

                writer.writerow([
                    datetime.now().isoformat(),
                    sensor_id,
                    round(accel_x, 4),
                    round(vibration_rms, 4),
                    round(impact_peak, 4),
                    impact_event,
                    overrange,
                    alerts
                ])
                t += dt
                time.sleep(dt)
        except KeyboardInterrupt:
            logger.info("Impact bed accelerometer simulation stopped")

if __name__ == "__main__":
    generate_impact_bed_accelerometer_data()
