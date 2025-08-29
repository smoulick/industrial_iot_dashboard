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
    g_range=100,
    sensitivity_mV_per_g=20,
    base_freq_hz=50,
    sample_rate_hz=100,
):
    project_root = Path(__file__).resolve().parents[3]
    output_path = project_root / "data_output/conveyor_belt/impact_bed_accelerometer.csv"
    print("Writing to:", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0

    t = 0
    dt = 1.0 / sample_rate_hz
    impact_duration = 0.2  # longer, smoother impact
    impact_samples = int(impact_duration * sample_rate_hz)
    impact_profile = np.zeros(impact_samples)
    impact_idx = 0
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
                # ✅ Realistic base signal
                base = 5.0 * np.sin(2 * np.pi * base_freq_hz * t)
                harmonic = 1.5 * np.sin(2 * np.pi * 3 * base_freq_hz * t)
                noise = np.random.normal(0, 0.8)  # stronger random noise
                accel_x = base + harmonic + noise

                # 🎯 Smooth impact spike simulation
                if impact_cooldown == 0 and np.random.rand() < 0.005:
                    peak = np.random.uniform(10, 25)
                    impact_profile = np.hanning(impact_samples) * peak
                    impact_cooldown = impact_samples
                    impact_idx = 0

                if impact_cooldown > 0:
                    accel_x += impact_profile[impact_idx]
                    impact_event = 1
                    impact_peak = impact_profile.max()
                    impact_idx += 1
                    impact_cooldown -= 1
                else:
                    impact_event = 0
                    impact_peak = 0

                overrange = int(abs(accel_x) > g_range)
                vibration_rms = np.sqrt(accel_x ** 2)

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
