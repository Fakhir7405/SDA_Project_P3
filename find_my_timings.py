"""
Run this script ONCE on your machine to find the correct config values
for Green / Yellow / Red backpressure demonstration.

Usage:
    python find_my_timings.py
"""
import hashlib
import time

print("=" * 60)
print("  Measuring hash speed on YOUR machine...")
print("=" * 60)

key   = "sda_spring_2026_secure_key"
value = "32.78"

times = []
for _ in range(3):
    start = time.time()
    hashlib.pbkdf2_hmac("sha256", key.encode(), value.encode(), 100000)
    times.append((time.time() - start) * 1000)

ms = sum(times) / len(times)

print(f"\n  One hash takes : {ms:.0f}ms on your machine")
print(f"  4 workers      : {4000/ms:.1f} rows/sec throughput")
print(f"  2 workers      : {2000/ms:.1f} rows/sec throughput")
print(f"  1 worker       : {1000/ms:.1f} rows/sec throughput")

red_delay    = round(ms / 4 / 1000 / 5,  4)
yellow_delay = round(ms / 2 / 1000 * 0.7, 4)
green_delay  = round(ms / 4 / 1000 * 3,  4)

print()
print("=" * 60)
print("  COPY THESE VALUES INTO config.json:")
print("=" * 60)
print()
print(f"  RED (Heavy backpressure):")
print(f"    input_delay_seconds : {red_delay}")
print(f"    core_parallelism    : 4")
print()
print(f"  YELLOW (Medium load):")
print(f"    input_delay_seconds : {yellow_delay}")
print(f"    core_parallelism    : 2")
print()
print(f"  GREEN (Smooth flow):")
print(f"    input_delay_seconds : {green_delay}")
print(f"    core_parallelism    : 4")
print()
print("=" * 60)