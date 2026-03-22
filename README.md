Phase 3 - Generic Concurrent Real-Time Data Pipeline


HOW TO RUN
----------
1. Install matplotlib (only external library needed):
   pip install -r requirements.txt

2. Put your CSV file inside the data/ folder.

3. Open config.json and update dataset_path to match your filename.

4. From the project root folder, run:
   python main.py

Note: Make sure you run from the root (where main.py is), not from inside
any subfolder.


FOLDER STRUCTURE
----------------
main.py              - entry point, run this
config.json          - all pipeline settings
requirements.txt     - just matplotlib
find_my_timings.py   - run this to get correct config values for your machine
utils.py             - shared helper functions

data/
  sample_climate_data.csv   - put your dataset here

plugins/
  inputs.py          - reads CSV, maps column names, casts types

core/
  engine.py          - signature verification + sliding window average
  contracts.py       - abstract protocols (DIP)

gui/
  dashboard.py       - live dashboard (Tkinter + Matplotlib)

telemetry/
  monitor.py         - telemetry subject for observer pattern

uml/
  class_diagram.puml / class_diagram.png
  sequence_diagram.puml / sequence_diagram.png


CONFIGURING FOR A NEW DATASET
------------------------------
The pipeline does not hardcode any column names. Everything is driven by
config.json so it works with any CSV without touching the code.

Steps:
1. Drop your CSV in data/
2. Change dataset_path in config.json
3. Update schema_mapping columns to match your CSV headers:

   source_name      = the actual column name in your CSV
   internal_mapping = rename it to one of:
                      entity_name, time_period, metric_value, security_hash
   data_type        = string, integer, or float

   For example, if your CSV has columns City / Year / Temp / Signature:

   "columns": [
     { "source_name": "City",      "internal_mapping": "entity_name",  "data_type": "string"  },
     { "source_name": "Year",      "internal_mapping": "time_period",  "data_type": "integer" },
     { "source_name": "Temp",      "internal_mapping": "metric_value", "data_type": "float"   },
     { "source_name": "Signature", "internal_mapping": "security_hash","data_type": "string"  }
   ]

4. Update the secret_key to match the key used to generate signatures in your CSV.
5. Run python main.py


IMPORTANT - CALIBRATE BEFORE DEMONSTRATING BACKPRESSURE
---------------------------------------------------------
The PBKDF2 hashing (100,000 iterations) runs at different speeds on every
machine. If you use fixed delay values the queue bars may not show the
expected Green / Yellow / Red behavior.

Before your demo, run this once:
   python find_my_timings.py

It measures hash speed on your specific machine and prints the exact
input_delay_seconds and core_parallelism values to use in config.json
for each backpressure scenario.


WHAT THE DASHBOARD SHOWS
-------------------------
Top row - four stat cards:
  Total Ingested  = rows pushed into the pipeline from CSV
  Total Verified  = rows that passed the signature check
  Total Processed = rows that completed the sliding window average
  Drop Rate       = percentage dropped due to bad/fake signatures

Left side - two matplotlib charts:
  Green line = live metric_value from each verified packet
  Blue line  = running average (computed_metric) over the window

Right side - queue telemetry bars:
  Raw Queue       = how full the Input -> Core queue is
  Verified Queue  = how full the Core -> Aggregator queue is
  Processed Queue = how full the Aggregator -> Dashboard queue is

  Green  = under 30% full
  Yellow = 30-70% full
  Red    = over 70% full (backpressure)


TESTING DIFFERENT SCENARIOS
-----------------------------
Wrong secret key:
  Change secret_key in config.json to anything wrong.
  Total Verified will stay 0. Charts stay empty.
  This proves the verification layer is actually working.

Window size effect:
  running_average_window_size = 3   -> blue line will be jumpy
  running_average_window_size = 30  -> blue line will be very smooth


COMMON ERRORS
--------------
ModuleNotFoundError: No module named 'matplotlib'
  -> pip install matplotlib

config.json not found
  -> You are running from the wrong folder. cd to the root first.

CSV file not found
  -> Check dataset_path in config.json matches your actual filename.

No schema columns matched
  -> source_name values in config.json do not match your CSV headers.
     They must match exactly (case-insensitive).

Charts empty, Total Verified = 0
  -> secret_key in config.json is wrong.
     Update it to match the key used to sign your CSV.

Queue bars not showing expected colors
  -> Run find_my_timings.py first to get the right values for your machine.



Why the Verified Queue always shows 0%
----------------------------------------
One thing that might look strange during the demo is that the Verified
Queue bar stays at 0% the whole time even though data is clearly flowing.
This is not a bug.
 
What happens is that the hashing takes long enough that by the time a
worker finishes verifying a row and puts it in the verified queue, the
Aggregator is already waiting and picks it up straight away. The whole
thing happens so fast that our dashboard (which only refreshes every
200ms) never gets a chance to catch anything sitting in that queue.
 
The proof that it is actually working is in the counters. If you watch
Total Verified go up and Total Processed match it, the verified queue
is doing its job fine. The charts drawing live data also confirms it.
 
The Raw Queue is the one you will see fill up and go red. That is where
the backpressure happens because input is pushing rows faster than the
workers can hash them, which is exactly what the project is supposed
to demonstrate.