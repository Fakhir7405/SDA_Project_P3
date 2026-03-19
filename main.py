import multiprocessing as mp
import threading
import json
import sys
from functools import reduce
from plugins.inputs import InputModule
from core.engine import core_worker, StateAggregator
from gui.dashboard import DashboardGUI
from telemetry.monitor import PipelineTelemetry


# It will load config file safely.
# If file is missing or broken,it will show an error and stop the program.

def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        print("[Main] ERROR: config.json not found. Place it in the project root.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[Main] ERROR: config.json is malformed JSON -> {e}")
        sys.exit(1)


# To make sure all required config keys exist.it will stop if any of them are missing.
REQUIRED_KEYS = [
    ["dataset_path"],
    ["pipeline_dynamics", "input_delay_seconds"],
    ["pipeline_dynamics", "core_parallelism"],
    ["pipeline_dynamics", "stream_queue_max_size"],
    ["schema_mapping", "columns"],
    ["processing", "stateless_tasks", "secret_key"],
    ["processing", "stateless_tasks", "iterations"],
    ["processing", "stateful_tasks", "running_average_window_size"],
    ["visualizations", "telemetry"],
    ["visualizations", "data_charts"],
]

def validate_config(config):
    # This function will check config for all required keys and exit with a message if any of them are missing.
    def check_key_path(key_path):
        node = config
        try:
            # Functional: reduce navigates nested dict path
            reduce(lambda d, k: d[k], key_path, config)
            return None
        except KeyError:
            return f"[Config] ERROR: Missing required key -> {' > '.join(key_path)}"

    errors = list(filter(None, map(check_key_path, REQUIRED_KEYS)))
    list(map(print, errors))

    if errors:
        print("[Config] Fix the above errors in config.json and try again.")
        sys.exit(1)

    # It will validate schema mapping that has at least one column defined
    columns = config["schema_mapping"]["columns"]
    if not isinstance(columns, list) or len(columns) == 0:
        print("[Config] ERROR: schema_mapping.columns must be a non-empty list.")
        sys.exit(1)

    # It will validate each column entry that has required sub keys.
    required_col_keys = ["source_name", "internal_mapping", "data_type"]

    def check_column(indexed_col):
        i, col = indexed_col
        missing = list(filter(lambda ck: ck not in col, required_col_keys))
        return (i, missing)

    col_errors = list(filter(lambda x: x[1], map(check_column, enumerate(columns))))

    if col_errors:
        list(map(lambda x: print(f"[Config] ERROR: Column {x[0]} missing keys: {x[1]}"), col_errors))
        sys.exit(1)

    if config["pipeline_dynamics"]["core_parallelism"] < 1:
        print("[Config] ERROR: core_parallelism must be >= 1.")
        sys.exit(1)

    if config["pipeline_dynamics"]["stream_queue_max_size"] < 1:
        print("[Config] ERROR: stream_queue_max_size must be >= 1.")
        sys.exit(1)

    if config["processing"]["stateful_tasks"]["running_average_window_size"] < 1:
        print("[Config] ERROR: running_average_window_size must be >= 1.")
        sys.exit(1)

    print("[Config] Validation passed. All required keys present.")


#Telemetry Timer
# It will keep checking the system in the background and tell the dashboard about what is happening.
def start_telemetry_timer(telemetry, interval=0.5):
 #This function will start a background thread that regularly tells telemetry to update the dashboard.
    def tick():
        try:
            telemetry.notify()
        except Exception as e:
            print(f"[Telemetry] ERROR in notify: {e}")
        t = threading.Timer(interval, tick)
        t.daemon = True
        t.start()

    t = threading.Timer(interval, tick)
    t.daemon = True
    t.start()



if __name__ == "__main__":
    mp.set_start_method("spawn")

    # Loading of config.
    config = load_config()

    # Validation of config.
    validate_config(config)

    dynamics  = config["pipeline_dynamics"]
    max_size  = dynamics["stream_queue_max_size"]
    n_workers = dynamics["core_parallelism"]

    #Queues
    raw_q       = mp.Queue(maxsize=max_size)
    verified_q  = mp.Queue(maxsize=max_size)
    processed_q = mp.Queue(maxsize=max_size)

    # Shared Counters
    raw_count       = mp.Value("i", 0)
    verified_count  = mp.Value("i", 0)
    processed_count = mp.Value("i", 0)

    # Firstly dashboard is created so that it can receive updates from the telemetry.
    gui = DashboardGUI(
        raw_q, verified_q, processed_q, max_size,
        raw_count, verified_count, processed_count,
        config
    )

    telemetry = PipelineTelemetry(raw_q, verified_q, processed_q, max_size)
    telemetry.attach(gui)

    input_p = mp.Process(
        target=InputModule.run,
        args=(config, raw_q, raw_count),
        daemon=True
    )

    workers = list(map(
        lambda _: mp.Process(
            target=core_worker,
            args=(config, raw_q, verified_q, verified_count),
            daemon=True
        ),
        range(n_workers)
    ))

    aggregator = mp.Process(
        target=StateAggregator.run,
        args=(config, verified_q, processed_q, processed_count),
        daemon=True
    )

    #Start
    input_p.start()
    list(map(lambda w: w.start(), workers))
    aggregator.start()
    
    #It will start the timer that updates the dashboard while the processes run.
    start_telemetry_timer(telemetry, interval=0.5)

    # GUI blocks here until the window is closed.
    gui.run()

    print("[Main] GUI closed. Shutting down workers...")

    input_p.terminate()
    list(map(lambda w: w.terminate(), workers))
    aggregator.terminate()

    input_p.join(timeout=3)
    list(map(lambda w: w.join(timeout=3), workers))
    aggregator.join(timeout=3)

    print("[Main] All processes terminated. Goodbye..")