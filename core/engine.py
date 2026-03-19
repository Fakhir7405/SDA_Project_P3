import hashlib
import time
from functools import reduce


#Pure Cryptographic Helper

def generate_signature(value, key, iterations):
   #This function make a security signature for the value using the key and number of iterations.
# This helps verify that the data has not been tampered with.
    return hashlib.pbkdf2_hmac(
        "sha256",
        key.encode("utf-8"),
        value.encode("utf-8"),
        iterations
    ).hex()


# These helpers functions check and validate rows using the internal names like metric_value, security_hash, and entity_name.
# it uses internal names means the code can work with any dataset that has been mapped, not just one specific CSV file.

def extract_metric(row):
    val = row.get("metric_value")
    if val is None:
        return ""
    return str(val).strip()

def is_valid_metric(raw):
   #This function make sure the metric is not empty. 
# It returna True if there is a value, False if it is empty.
    return raw != ""

def to_float(raw):
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None

def format_value(raw):
    parsed = to_float(raw)
    return "{:.2f}".format(parsed) if parsed is not None else None

def signature_matches(val, row, key, iterations):
   #This function checks if the packet has the correct security signature.
# Return True if it matches, False if it is missing or wrong.
    stored_hash = row.get("security_hash", "")
    if not stored_hash:
        return False
    return generate_signature(val, key, iterations) == stored_hash


#Pure Row Processing (core_worker)

def parse_verified_row(row, key, iterations):
    # This function check one verified packet to make sure it is valid and the signature is correct.
# If anything is wrong, return None to drop it; otherwise, return the packet.
    raw = extract_metric(row)
    if not is_valid_metric(raw):
        return None
    val = format_value(raw)
    if val is None:
        return None
    if not signature_matches(val, row, key, iterations):
        return None
    return row


def process_single_raw(raw_q, verified_q, key, iterations, verified_count):
    # This function take one packet from the raw queue, check if it is valid, and put it into the verified queue.
# If we get a special signal (None) or an error happens, handle it safely.
    try:
        row = raw_q.get()
    except Exception as e:
        print(f"[CoreWorker] ERROR reading raw_q: {e}")
        return True

    # None means input stream is exhausted
    if row is None:
        return False

    result = parse_verified_row(row, key, iterations)

    if result is not None:
        try:
            verified_q.put(result)
            with verified_count.get_lock():
                verified_count.value += 1
        except Exception as e:
            print(f"[CoreWorker] ERROR writing verified_q: {e}")

    return True


def run_core_loop(raw_q, verified_q, key, iterations, verified_count):
    # This function keep taking one raw packet at a time, process it, and put it into the verified queue.
# It stops safely when a special signal (None) is received instead of running forever.
    def step(_, __):
        keep_going = process_single_raw(raw_q, verified_q, key, iterations, verified_count)
        if not keep_going:
            raise StopIteration
        return None

    try:
        reduce(step, iter(int, 1), None)
    except StopIteration:
        pass


def core_worker(config, raw_q, verified_q, verified_count):
# This function takes raw data, checks it, and puts verified data into another queue.
# It reads the secret key and number of iterations from the config to do its work.
# When it finishes, it prints a message saying it stopped safely.
    key        = config["processing"]["stateless_tasks"]["secret_key"]
    iterations = config["processing"]["stateless_tasks"]["iterations"]
    run_core_loop(raw_q, verified_q, key, iterations, verified_count)
    print("[CoreWorker] Exited cleanly.")


#Pure Sliding Window Helpers (State Aggregator)

def updated_window(window, value, size):
    new_window = window + [value]
    return new_window[-size:]

def compute_avg(window):
    return sum(window) / len(window) if window else 0.0

def build_output_packet(row, value, window):
    # This function create the final output packet from a row.
# It includes the entity name, time period, metric value, and computed average.
    return {
        "entity_name":     row.get("entity_name", "unknown"),
        "time_period":     row.get("time_period", 0),
        "metric_value":    value,
        "computed_metric": compute_avg(window),
    }

def parse_verified_value(row):
# This function uses extract_metric with the correct key "metric_value".
    raw = extract_metric(row)
    return to_float(raw)


    #Aggregation Step

def aggregate_single(state, verified_q, processed_q, size, processed_count):
    """
   This function takes one verified item, calculates a running average,then sends the result. 
    It also keeps track of the current state. 
    Then it safely stops when it sees a special signal and handles any queue errors.
    """
    try:
        row = verified_q.get()
    except Exception as e:
        print(f"[Aggregator] ERROR reading verified_q: {e}")
        return state
    
       #When we get a special signal (None), pass it on and stop the process safely.

    if row is None:
        raise StopIteration

    value = parse_verified_value(row)

    if value is None:
        return state                        # The item is dropped, and the counter is not changed.

    new_window = updated_window(state, value, size)
    packet     = build_output_packet(row, value, new_window)

    try:
        processed_q.put(packet)
        with processed_count.get_lock():
            processed_count.value += 1
    except Exception as e:
        print(f"[Aggregator] ERROR writing processed_q: {e}")

    return new_window


def run_aggregator_loop(verified_q, processed_q, size, processed_count):
    """
  This loop collects data for aggregation. 
   It stops safely when it sees a special signal (StopIteration).
   """
    def step(window, __):
        return aggregate_single(window, verified_q, processed_q, size, processed_count)

    try:
        reduce(step, iter(int, 1), [])
    except StopIteration:
        pass


class StateAggregator:
    @staticmethod
       #This class takes data from the verified and processed queues and calculates a running average. 
        #It uses the window size from the config to decide how many items to include in the average. 
        #When it finishes, it prints a message saying it stopped safely.
      
    def run(config, verified_q, processed_q, processed_count):
        size = config["processing"]["stateful_tasks"]["running_average_window_size"]
        run_aggregator_loop(verified_q, processed_q, size, processed_count)
        print("[Aggregator] Exited cleanly.")