# This module has helper fucntions that can be used anywhere in the program.
# Putting them all here will let all modules use them without causing errors.

import json
import sys


def load_config(path="config.json"):
    # This funciton will open the config file and read its settings.
# If the file is missing or broken,it will print an error and stop the program.
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Utils] ERROR: Config file not found -> {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[Utils] ERROR: Config file is malformed JSON -> {e}")
        sys.exit(1)


def safe_cast(value, data_type):
   # This function will try to turn a value into a number or string safely.
# If it can't be converted, it will return None instead of crashing.
    try:
        if data_type == "integer":
            return int(float(value))
        if data_type == "float":
            return float(value)
        return str(value).strip()
    except (ValueError, TypeError):
        return None


def clamp(value, min_val, max_val):
    # This function Keeps a number inside a range. 
# If it is too small,it will set it to the minimum. 
# If it is too big,it will set it to the maximum.
    return max(min_val, min(max_val, value))


def safe_ratio(numerator, denominator):
    # This function divide two numbers safely. 
# If the bottom number is zero, it will return 0.0 instead of crashing.
    return numerator / denominator if denominator > 0 else 0.0


def format_float(value, decimals=2):
    # This function turn a number into a float with a set number of decimal places.
# If the value is not a number, it will return 0.0
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return 0.0