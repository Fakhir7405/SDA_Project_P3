import csv
import time
from functools import reduce


#Type Casting
# Type casting is done to convert values to the right type safely.
#And if conversion fails, return None so the row can be removed later without crashing.

def cast_value(value, data_type):
    #This function will convert a value to the correct type (integer, float, or string).
# If it can't be converted, return None instead of crashing.
    try:
        if data_type == "integer":
            return int(float(value))
        if data_type == "float":
            return float(value)
        return str(value).strip()
    except (ValueError, TypeError):
        return None


#Schema Mapping

def build_schema_map(config):
   #This function creates a mapping that tells how to rename fields and what type each value should be.
# This helps in  matching CSV column names to the names used inside the program.
    columns = config["schema_mapping"]["columns"]
    return {
        col["source_name"].lower().strip(): (col["internal_mapping"], col["data_type"])
        for col in columns
    }


def apply_schema(row, schema_map):
   # This function will take one row and change its field names based on the schema.
#It will also convert each value to the correct type.
# It will ignore the fields that are not in the schema.
# If a value can't be converted, it will be set to None.
    def map_field(acc, item):
        source_key, (internal_name, data_type) = item
        raw_val = row.get(source_key, None)
        if raw_val is None:
            return acc
        casted = cast_value(raw_val, data_type)
        acc[internal_name] = casted
        return acc

    return reduce(map_field, schema_map.items(), {})


def is_complete_packet(packet):
    #This function will check if all values in the packet are filled.
# It will return True if nothing is missing or empty, otherwise False.
    return all(v is not None and v != "" for v in packet.values())


#CSV Reading & Cleaning

def normalize_key(k):
    return k.lower().strip() if k else ""

def normalize_value(v):
    return v.strip() if isinstance(v, str) else v

def clean_row(row):
    return {normalize_key(k): normalize_value(v) for k, v in row.items()}

def is_empty_row(row):
    return all(v == "" for v in row.values())

def is_valid_row(row):
    return not is_empty_row(row)

def read_csv_rows(path):
   # This function read rows from a CSV file.
# If the file is missing, empty, or can not be opened,it will show a message and return an empty list.
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                print(f"[InputModule] WARNING: CSV file is empty -> {path}")
            return rows
    except FileNotFoundError:
        print(f"[InputModule] ERROR: CSV file not found -> {path}")
        print(f"[InputModule] Check 'dataset_path' in config.json points to the correct file.")
        return []
    except PermissionError:
        print(f"[InputModule] ERROR: Permission denied reading -> {path}")
        return []
    except Exception as e:
        print(f"[InputModule] ERROR: Could not read CSV -> {e}")
        return []

def clean_all_rows(rows):
    return list(map(clean_row, rows))

def filter_valid_rows(rows):
    return list(filter(is_valid_row, rows))

def apply_schema_to_all(rows, schema_map):
    #This function will go through all rows and rename fields based on the schema.
# It will also convert values to the right types and remove any incomplete rows.
    mapped = list(map(lambda row: apply_schema(row, schema_map), rows))
    return list(filter(is_complete_packet, mapped))


#Schema Mismatch Detection
# To check if the CSV headers match what we expect in the schema.
# If nothing matches,then it will show a clear message so the user knows what is wrong.

def check_schema_match(raw_rows, schema_map):
   # This function will check if the CSV headers match the expected schema.
# It will print an error if nothing matches, and a warning if some columns are missing.
# It will return True if at least one column matches, otherwise False.
    if not raw_rows:
        return False

    actual_headers  = set(normalize_key(k) for k in raw_rows[0].keys())
    expected_keys   = set(schema_map.keys())
    matched         = actual_headers & expected_keys
    missing         = expected_keys - actual_headers

    if not matched:
        print("[InputModule] ERROR: No schema columns matched the CSV headers.")
        print(f"[InputModule] CSV headers found    : {sorted(actual_headers)}")
        print(f"[InputModule] schema_mapping expects: {sorted(expected_keys)}")
        print("[InputModule] Fix 'source_name' values in config.json schema_mapping.")
        return False

    if missing:
        print(f"[InputModule] WARNING: Some schema columns not found in CSV: {sorted(missing)}")
        print("[InputModule] Rows missing these columns will be dropped.")

    return True


def get_valid_mapped_rows(path, schema_map):
   
#Complete input process: read the data, clean it, remove empty rows,
#check that it matches the schema, apply the schema mapping, and remove any incomplete rows.

    raw_rows     = read_csv_rows(path)

    if not raw_rows:
        return []
# It make sure the input data matches the expected schema before starting processing.
    if not check_schema_match(raw_rows, schema_map):
        return []

    cleaned_rows = clean_all_rows(raw_rows)
    valid_rows   = filter_valid_rows(cleaned_rows)
    mapped_rows  = apply_schema_to_all(valid_rows, schema_map)

# It will print a warning if the schema mapping removed all the rows and there is nothing to process.
    if not mapped_rows:
        print("[InputModule] ERROR: 0 valid rows after schema mapping.")
        print("[InputModule] Possible causes:")
        print("  1. 'source_name' in schema_mapping doesn't match CSV column headers exactly.")
        print("  2. 'data_type' mismatch — e.g. 'float' column contains non-numeric values.")
        print("  3. Required columns have empty values in every row.")

    return mapped_rows


#Enqueue with Sentinel 

# These below functions put rows into the raw queue one by one.
# Keep track of how many rows were added and wait a little between each row.
# This sends all rows to the workers for processing.
def enqueue_row(raw_q, delay, raw_count, row):
    raw_q.put(row)
    with raw_count.get_lock():
        raw_count.value += 1
    time.sleep(delay)
    return row

def enqueue_all_rows(rows, raw_q, delay, raw_count):
    return reduce(
        lambda _, row: enqueue_row(raw_q, delay, raw_count, row),
        rows,
        None
    )

def push_sentinels(raw_q, num_workers):
    # Send one special signal (None) for each worker so that they can know there is no more data.
    reduce(lambda _, __: raw_q.put(None), range(num_workers), None)


#InputModule 

class InputModule:
    @staticmethod
    def run(config, raw_q, raw_count):
        path        = config["dataset_path"]
        delay       = config["pipeline_dynamics"]["input_delay_seconds"]
        num_workers = config["pipeline_dynamics"]["core_parallelism"]
        schema_map  = build_schema_map(config)

        print(f"[InputModule] Reading from: {path}")
        print(f"[InputModule] Schema mapping: {list(schema_map.keys())} -> {[v[0] for v in schema_map.values()]}")

        rows = get_valid_mapped_rows(path, schema_map)
# If there are no valid rows, send special signals (None) so workers stop safely
# and don't get stuck waiting for data.
        if not rows:
            print("[InputModule] No rows to enqueue. Sending stop signals to workers.")
            push_sentinels(raw_q, num_workers)
            return

        print(f"[InputModule] {len(rows)} valid rows ready to stream.")
        enqueue_all_rows(rows, raw_q, delay, raw_count)

# After sending all the data,it will send special signals (None) so workers know to stop.
        push_sentinels(raw_q, num_workers)
        print(f"[InputModule] Done. {raw_count.value} rows enqueued.")