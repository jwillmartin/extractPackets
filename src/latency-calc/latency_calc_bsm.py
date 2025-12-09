#!/usr/bin/env python3
import numpy as np
import tkinter as tk
from tkinter import filedialog
from typing import Literal

def select_files() -> tuple[str, ...] | Literal['']:
    """Open a file dialog to select two CSV files and return their paths as a list."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_paths = filedialog.askopenfilenames(title="Select BSM Files", filetypes=[("Decoded BSM Files", "*.csv"), ("All Files", "*.*")])
    return file_paths

def get_timestamps(file_path) -> dict[float, str]:
    """Extract timestamps and payloads from the given CSV file.
    Return:
        dict: A dictionary with timestamps as keys and payloads as values.
    """
    timestamps = {}
    print(f"Processing file: {file_path}")
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip():  # Ensure the line is not empty
                parts = line.split(',')
                try:
                    timestamp = float(parts[0])  # timestamp is the first column
                    payload = parts[10] if len(parts) > 10 else None
                    timestamps[timestamp] = payload
                except ValueError:
                    continue  # Skip lines where conversion fails
    return timestamps

def get_tx_ipg(
    timestamps: dict[float, str], *, expected_ipg: float = 0.100, gap_factor: float = 3.0
) -> None:
    """Calculate and print the inter-packet gap (IPG) for transmitted packets.

    Args:
        timestamps: Mapping of timestamp -> payload (only keys are used here)
        expected_ipg: Expected nominal IPG in seconds (default 0.100s = 100ms)
        gap_factor: Any interval greater than expected_ipg * gap_factor is treated
                    as a discontinuity (e.g., a merged-file gap) and excluded
                    from the IPG mean calculation.
    """
    print("Calculating Transmit Inter-Packet Gap (IPG)...")
    if not timestamps or len(timestamps) < 2:
        print("Not enough data to calculate IPG.")
        return

    # Sort timestamps to ensure strictly increasing series for diff
    ipg_timestamps = sorted(timestamps.keys())

    # Compute successive differences
    diffs = np.diff(ipg_timestamps)

    # Determine threshold for "significant" gaps (e.g., merged file break)
    # Use both a dynamic threshold (gap_factor * median) and a floor based on expected_ipg
    median_diff = float(np.median(diffs)) if len(diffs) else expected_ipg
    dynamic_thresh = median_diff * gap_factor
    absolute_thresh = expected_ipg * gap_factor
    gap_threshold = max(dynamic_thresh, absolute_thresh)

    # Identify and filter out large gaps
    large_gap_mask = diffs > gap_threshold
    num_large_gaps = int(np.count_nonzero(large_gap_mask))
    filtered_diffs = diffs[~large_gap_mask]

    if num_large_gaps > 0:
        max_gap = float(np.max(diffs)) if len(diffs) else 0.0
        print(
            f"Warning: Detected {num_large_gaps} large gap(s) (> {gap_threshold*1000:.0f} ms). "
            "Excluding them from IPG calculation."
        )
        print(f"Max observed gap: {max_gap*1000:.2f} ms")

    # If everything got filtered (extreme case), fall back to median of original diffs
    if filtered_diffs.size == 0:
        ipg = median_diff
        note = " (median, no valid diffs after filtering)"
    else:
        ipg = float(np.mean(filtered_diffs))
        note = " (filtered)" if num_large_gaps > 0 else ""

    print(f"Transmit IPG: {ipg*1000:.2f} ms{note}")

def get_metrics(timestamps: dict[float, str]) -> None:
    """Calculate basic latency metrics between two timestamps, by payload value."""
    print("Calculating Latency Metrics...")
    latencies = []

    # Basic latency statistics
    sorted_timestamps = sorted(timestamps.items())
    for i in range(1, len(sorted_timestamps)):
        t1, payload1 = sorted_timestamps[i - 1]
        t2, payload2 = sorted_timestamps[i]
        if payload1 == payload2 and payload1 is not None:
            latencies.append(t2 - t1)
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    mean_latency = float(np.mean(latencies)) if latencies else 0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0
    p99_latency = float(np.percentile(latencies, 99)) if latencies else 0

    # Jitter metrics: difference between successive samples of the latency series
    diffs = np.diff(latencies)
    abs_diffs = np.abs(diffs) if len(diffs) else np.array([0.0])
    avg_jitter = float(np.mean(abs_diffs))
    std_jitter = float(np.std(abs_diffs))

    print(f"Min: {min_latency*1000:.2f} ms")
    print(f"Max: {max_latency*1000:.2f} ms")
    print(f"Avg: {mean_latency*1000:.2f} ms")
    print(f"95th Percentile: {p95_latency*1000:.2f} ms")
    print(f"99th Percentile: {p99_latency*1000:.2f} ms")
    print(f"Avg Jitter: {avg_jitter*1000:.2f} ms")
    print(f"Std Jitter: {std_jitter*1000:.2f} ms")

if __name__ == "__main__":
    selected_files = select_files()
    timestamps = {}
    if len(selected_files) == 2:
        for file in selected_files:
            ts = get_timestamps(file)
            timestamps.update(ts)

    if timestamps:
        get_metrics(timestamps)
        for file in selected_files:
            tx_file = file.find("tx")
            if tx_file != -1:
                tx_timestamps = get_timestamps(file)
                get_tx_ipg(tx_timestamps)
    else:
        print("No files selected or no data found.")
