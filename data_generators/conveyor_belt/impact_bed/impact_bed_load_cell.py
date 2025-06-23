import numpy as np
import time
import csv
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_load_cell_data(
    output_path="data_output/conveyor_belt/impact_bed_load_cell.csv",
    sensor_id="SGLC7050-IMPACTBED-001",
    loadcell_capacity_kN=2000,  # Choose from datasheet: 1000, 2000, 3000, 5000, 10000
    rated_output_mV_per_V=1.5,  # SGLC-7050 typical
    excitation_V=10.0,
    temp_nom_C=25.0,
    temp_effect_per_C=0.0001,  # 0.01% per °C
    sample_rate_hz=1
):
    project_root = Path(__file__).resolve().parents[3]  # [3] for .../data_generators/conveyor_belt/pulley/
    output_path = project_root / "data_output/conveyor_belt/impact_bed_load_cell.csv"
    print("Writing to:", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    # Pattern: 24-hour cycle, ramp up (6-8am), steady (8am-6pm), ramp down (6-8pm), idle (else)
    seconds_in_day = 24 * 3600
    impact_interval_s = 47  # Impact every 47 seconds, for visible pattern
    impact_duration_s = 2   # Impact lasts 2 seconds

    t0 = time.time()
    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "timestamp", "sensor_id", "applied_load_kN",
                "mv_per_v", "excitation_V", "temperature_C",
                "impact_event", "alerts"
            ])
        try:
            while True:
                now = datetime.now()
                t = (time.time() - t0) % seconds_in_day
                hour = now.hour + now.minute/60.0

                # Simulate daily load cycle (patterned, not random)
                if 6 <= hour < 8:
                    # Ramp up
                    applied_load = loadcell_capacity_kN * ((hour-6)/2) * 0.8
                elif 8 <= hour < 18:
                    # Steady load
                    applied_load = loadcell_capacity_kN * 0.8
                elif 18 <= hour < 20:
                    # Ramp down
                    applied_load = loadcell_capacity_kN * (1 - (hour-18)/2) * 0.8
                else:
                    # Idle
                    applied_load = loadcell_capacity_kN * 0.05

                # Add periodic impact event (sharp spike)
                seconds_today = (now.hour*3600 + now.minute*60 + now.second)
                impact_phase = seconds_today % impact_interval_s
                if impact_phase < impact_duration_s:
                    impact_event = 1
                    impact_load = loadcell_capacity_kN * 0.2
                else:
                    impact_event = 0
                    impact_load = 0

                total_load = applied_load + impact_load

                # Simulate temperature drift (slow daily sinusoidal)
                temperature = temp_nom_C + 10*np.sin(2*np.pi*(t/seconds_in_day))

                # mV/V output calculation (datasheet: output = 1.5 mV/V at full scale)
                mv_per_v = (total_load / loadcell_capacity_kN) * rated_output_mV_per_V
                # Add temperature effect
                mv_per_v = mv_per_v * (1 + temp_effect_per_C * (temperature - temp_nom_C))

                # Alerts
                if total_load > loadcell_capacity_kN * 1.5:
                    alerts = "OVERLOAD"
                elif impact_event:
                    alerts = "IMPACT"
                else:
                    alerts = "NORMAL"

                writer.writerow([
                    now.isoformat(),
                    sensor_id,
                    round(total_load, 2),
                    round(mv_per_v, 5),
                    excitation_V,
                    round(temperature, 2),
                    impact_event,
                    alerts
                ])
                time.sleep(1/sample_rate_hz)
        except KeyboardInterrupt:
            logger.info("Impact bed load cell simulation stopped")

if __name__ == "__main__":
    generate_load_cell_data()
