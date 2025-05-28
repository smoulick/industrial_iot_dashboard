# In D:\Project\industrial_iot_dashboard\main_data_generator.py
import yaml
from pathlib import Path
import threading
import time
import importlib  # For dynamically importing sensor modules
import logging

# Configure basic logging for the main generator
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [MainGenerator] - %(message)s')
logger = logging.getLogger(__name__)

# Define base paths
ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_OUTPUT_DIR = ROOT_DIR / "data_output"


def load_config(config_file_name: str):
    config_path = CONFIG_DIR / config_file_name
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file {config_path} not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML in {config_path}: {e}")
        return None


def run_sensor_process(sensor_module_name, sensor_function_name, base_output_dir, sensor_config):
    """
    Imports and runs a sensor generation function.
    sensor_config is the specific dictionary for one sensor instance from the YAML.
    """
    try:
        module_path_for_import = sensor_module_name.replace("/", ".").replace("\\", ".")
        module = importlib.import_module(module_path_for_import)
        sensor_function = getattr(module, sensor_function_name)

        params_for_function = sensor_config.copy()
        output_file_name = params_for_function.pop("output_file",
                                                   f"{sensor_config.get('sensor_id', 'default_sensor')}_data.csv")
        params_for_function["output_file_path"] = base_output_dir / output_file_name
        params_for_function.pop("enabled", None)

        sensor_id = params_for_function.get('sensor_id', 'N/A_SENSOR_ID')
        logger.info(
            f"Attempting to start sensor: {sensor_id} using function {sensor_function_name} from module {module_path_for_import}")
        logger.info(f"Sensor parameters for {sensor_id}: {params_for_function}")

        sensor_function(**params_for_function)
        logger.info(f"Sensor {sensor_id} finished or exited.")

    except ModuleNotFoundError:
        logger.error(f"Sensor module {module_path_for_import} not found.")
    except AttributeError:
        logger.error(f"Function {sensor_function_name} not found in {module_path_for_import}.")
    except Exception as e:
        sensor_id_for_error = sensor_config.get('sensor_id', 'UNKNOWN_SENSOR')
        logger.error(f"Error running sensor {sensor_id_for_error}: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting main data generator orchestration...")
    active_threads = []

    conveyor_config_data = load_config("conveyor_belt_config.yml")
    if conveyor_config_data:
        asset_type = conveyor_config_data.get("asset_type", "unknown_asset")
        asset_specific_output_dir = DATA_OUTPUT_DIR / asset_type
        asset_specific_output_dir.mkdir(parents=True, exist_ok=True)

        for sensor_type, sensor_instances_list in conveyor_config_data.get("sensors", {}).items():
            module_name = ""
            function_to_call = ""

            if sensor_type == "ultrasonic":
                module_name = f"data_generators.{asset_type}.ultrasonic_sensor"
                function_to_call = "generate_ultrasonic_data"
            elif sensor_type == "inductive":
                module_name = f"data_generators.{asset_type}.inductive_sensor"
                function_to_call = "generate_inductive_data"
            # --- Add new elif block for heat sensors ---
            elif sensor_type == "heat_sensor":  # Matches the key in your YAML
                module_name = f"data_generators.{asset_type}.heat_sensor"  # Points to the new script
                function_to_call = "generate_heat_data"  # The function in heat_sensor.py
            # --- End of new block ---
            else:
                logger.warning(f"Unknown sensor type '{sensor_type}' in config. Skipping.")
                continue

            if module_name and function_to_call:
                for single_sensor_config in sensor_instances_list:
                    if single_sensor_config.get("enabled", False):
                        thread = threading.Thread(
                            target=run_sensor_process,
                            args=(module_name, function_to_call, asset_specific_output_dir, single_sensor_config),
                            daemon=True
                        )
                        active_threads.append(thread)
                        thread.start()
                    else:
                        logger.info(
                            f"Sensor '{single_sensor_config.get('sensor_id', 'N/A')}' of type '{sensor_type}' is disabled in config.")

    if not active_threads:
        logger.warning("No active sensor simulations were started. Check configurations.")
    else:
        logger.info(f"Launched {len(active_threads)} sensor simulation thread(s).")
        logger.info("Main generator will keep running. Press Ctrl+C to stop.")
        try:
            while any(t.is_alive() for t in active_threads):
                time.sleep(1)
            logger.info("All sensor threads have completed their run duration or exited.")
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received in main generator. Shutting down...")
        finally:
            for i, t in enumerate(active_threads):
                if t.is_alive():
                    logger.info(f"Thread {i + 1} for a sensor might still be processing shutdown...")
            logger.info("Main data generator process finished.")