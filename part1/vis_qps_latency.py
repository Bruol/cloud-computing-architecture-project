import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""
This script creates a visualization showing P95 latency vs QPS across different
interference configurations for memcached benchmarks. It processes multiple benchmark
files, averages across runs, and produces a clean, publication-quality plot.
"""

# Define the configuration types we're analyzing
config_types = ["none", "cpu", "l1d", "l1i", "l2", "llc", "membw"]
num_runs = 3  # Number of runs per configuration
log_dir = "./logs"  # Directory containing the benchmark logs

# Visual styling elements
colors = [
    "blue",
    "red",
    "green",
    "orange",
    "purple",
    "brown",
    "black",
]  # Distinct colors for each config
markers = ["o", "s", "^", "D", "*", "x", "+"]  # Distinct markers for each config


def parse_benchmark_file(file_path):
    """
    Parse a memcached benchmark file to extract relevant performance metrics.

    The file format has rows starting with 'read' containing latency percentiles and QPS data.
    Each row represents measurements for a particular target QPS level.

    Args:
        file_path: Path to the benchmark results file

    Returns:
        List of dictionaries, each containing parsed metrics for one QPS level
    """
    data = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            # Skip the header line containing column names
            for line in lines[1:]:
                if line.startswith("read"):  # Lines with actual data start with 'read'
                    parts = line.split()
                    if len(parts) >= 17:  # Ensure we have all expected columns
                        # Extract the specific metrics we need for this plot
                        row = {
                            # Average latency (not used in this plot but useful for reference)
                            "avg": float(parts[1]) / 1000.0,  # Convert μs to ms
                            # 95th percentile latency - our key metric of interest
                            "p95": float(parts[12]) / 1000.0,  # Convert μs to ms
                            # Actual QPS achieved (not the target QPS)
                            "actual_qps": float(parts[16]),
                            # Target QPS that was requested
                            "target_qps": float(parts[17]),
                            # Extract configuration type from filename
                            "config": os.path.basename(file_path).split("_")[2],
                            # Extract run number from filename
                            "run": int(
                                os.path.basename(file_path).split("_")[3].split(".")[0]
                            ),
                        }
                        data.append(row)

                # Stop processing at warning lines (end of useful data)
                if line.startswith("Warning"):
                    break
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return data


# PHASE 1: DATA COLLECTION
# ------------------------
print("Phase 1: Collecting benchmark data...")
all_data = []  # Will hold all parsed data points

# Iterate through each configuration and run
for config in config_types:
    for i in range(num_runs):
        file_pattern = f"{log_dir}/benchmark_results_{config}_{i}.txt"
        if os.path.exists(file_pattern):
            # Parse and collect data from this file
            data = parse_benchmark_file(file_pattern)
            all_data.extend(data)
        else:
            print(f"Warning: {file_pattern} not found")

# Check if we found any data
if not all_data:
    print("No data found. Check your log directory and file patterns.")
    exit(1)

# PHASE 2: DATA PROCESSING
# ------------------------
print("Phase 2: Processing data...")

# Convert collected data to a pandas DataFrame for easier manipulation
df = pd.DataFrame(all_data)

# Group by configuration and target QPS to calculate statistics across runs
# This computes mean and standard deviation for each metric across the runs
avg_df = (
    df.groupby(["config", "target_qps"])
    .agg(
        {
            "actual_qps": ["mean", "std"],  # Mean and std dev of achieved QPS
            "p95": ["mean", "std"],  # Mean and std dev of P95 latency
        }
    )
    .reset_index()
)

# Flatten the column hierarchy created by the aggregation
avg_df.columns = ["_".join(col).strip("_") for col in avg_df.columns.values]

# PHASE 3: VISUALIZATION
# ---------------------
print("Phase 3: Creating visualization...")

# Create a new figure with appropriate size for publication
plt.figure(figsize=(10, 6))

# Plot each configuration as a separate line
for i, config in enumerate(config_types):
    # Extract data for this configuration
    config_data = avg_df[avg_df["config"] == config].sort_values("actual_qps_mean")

    if not config_data.empty:
        # Plot line with error bars
        plt.plot(
            config_data["actual_qps_mean"],  # X-axis: mean achieved QPS
            config_data["p95_mean"],  # Y-axis: mean P95 latency
            f"{markers[i]}-",  # Line style with marker
            color=colors[i],  # Line color
            label=config.upper(),  # Legend label
            linewidth=2,  # Thicker line for visibility
            markersize=8,  # Larger markers for clarity
        )

# Set axis limits and labels
plt.xlim(0, 80000)  # X-axis from 0 to 80K QPS as specified
plt.xlabel("Actual Queries Per Second (QPS)", fontsize=14)
plt.ylabel("95th Percentile Latency (ms)", fontsize=14)  # Changed from μs to ms
plt.title(
    "Memcached P95 Latency vs QPS Under Different Interference Types", fontsize=16
)

# Add grid for easier reading
plt.grid(True, linestyle="--", alpha=0.7)

# Add legend to identify configurations
plt.legend(fontsize=12, loc="best")

# Add explanatory note about data averaging
plt.figtext(
    0.5,
    0.01,
    f"Note: Each data point represents the average of {num_runs} runs.",
    ha="center",
    fontsize=10,
)

# Ensure tight layout for best appearance
plt.tight_layout(pad=2.0)

# Save the visualization to a file
output_file = "memcached_p95_qps_plot.png"
plt.savefig(output_file, dpi=300, bbox_inches="tight")

# Create a version with log-scale y-axis for better visualization of the hockey-stick effect
# plt.yscale('log')
plt.ylabel(
    "95th Percentile Latency (ms, log scale)", fontsize=14
)  # Changed from μs to ms
plt.title("Memcached P95 Latency vs QPS (Log Scale)", fontsize=16)
plt.savefig("memcached_p95_qps_plot_log.png", dpi=300, bbox_inches="tight")

print(
    f"Plots saved as 'memcached_p95_qps_plot.png' and 'memcached_p95_qps_plot_log.png'"
)
plt.show()
