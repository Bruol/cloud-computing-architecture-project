#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import json
from datetime import datetime
import os
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Define colors for visualizing different PARSEC workloads
JOB_COLORS = {
    "parsec-blackscholes": "#CCA000",
    "parsec-canneal": "#CCCCAA",
    "parsec-dedup": "#CCACCA",
    "parsec-ferret": "#AACCCA",
    "parsec-freqmine": "#0CCA00",
    "parsec-radix": "#00CCA0",
    "parsec-vips": "#CC0A00",
}

# Node name mapping for better readability
NODE_NAMES = {
    "node-a-2core": "Node A (2 core)",
    "node-b-2core": "Node B (2 core)",
    "node-c-4core": "Node C (4 core)",
    "node-d-4core": "Node D (4 core)",
}


def parse_mcperf_data(file_path):
    """Parse mcperf data with Unix epoch timestamps, applying a 2-hour correction."""
    data = []
    # Correction for the 2-hour time difference (2 hours = 7,200,000 milliseconds)
    TIME_CORRECTION_MS = 7200000

    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split()
            if parts[0] == "read" and len(parts) >= 16:
                # Get raw Unix epoch timestamps in milliseconds and apply time correction
                ts_start_ms = int(parts[-2]) - TIME_CORRECTION_MS
                ts_end_ms = int(parts[-1]) - TIME_CORRECTION_MS
                p95 = float(parts[12])
                data.append((ts_start_ms, ts_end_ms, p95))
    return data


def parse_datetime(dt_str):
    """Parse Kubernetes datetime string to Python datetime object."""
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")


def process_pods_file(file_path):
    """Process a pods JSON file and extract job information with epoch timestamps."""
    with open(file_path, "r") as f:
        data = json.load(f)

    job_info = {}
    earliest_start_ms = None

    # Process each pod
    for pod in data.get("items", []):
        # Check if the pod is part of a job
        metadata = pod.get("metadata", {})
        labels = metadata.get("labels", {})

        # Find job name from labels
        job_name = labels.get("job-name") or labels.get("batch.kubernetes.io/job-name")

        if job_name and "parsec" in job_name:  # Only consider parsec jobs
            status = pod.get("status", {})
            spec = pod.get("spec", {})

            # Try to get startTime from status
            start_time = status.get("startTime")

            # If not available, check container statuses
            if not start_time:
                for container in status.get("containerStatuses", []):
                    if "state" in container and "terminated" in container["state"]:
                        if "startedAt" in container["state"]["terminated"]:
                            start_time = container["state"]["terminated"]["startedAt"]
                            break

            if not start_time:
                continue

            # Find container completion time
            completion_time = None
            for container in status.get("containerStatuses", []):
                if "state" in container and "terminated" in container["state"]:
                    if "finishedAt" in container["state"]["terminated"]:
                        completion_time = container["state"]["terminated"]["finishedAt"]
                        break

            if start_time and completion_time:
                # Convert to datetime and then to epoch milliseconds for consistency with mcperf
                start_dt = parse_datetime(start_time)
                completion_dt = parse_datetime(completion_time)

                start_ms = int(start_dt.timestamp() * 1000)  # Convert to milliseconds
                end_ms = int(
                    completion_dt.timestamp() * 1000
                )  # Convert to milliseconds

                # Get node information
                node_name = spec.get("nodeName", "unknown")

                # Update earliest start time
                if earliest_start_ms is None or start_ms < earliest_start_ms:
                    earliest_start_ms = start_ms

                # Store job information
                job_info[job_name] = {
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "node": node_name,
                    "exec_time_ms": end_ms - start_ms,
                }

    return job_info, earliest_start_ms


def create_plots(run_number):
    mcperf_file = f"part_3_results_group_020/mcperf_{run_number}.txt"
    pods_file = f"part_3_results_group_020/pods_{run_number}.json"

    if not os.path.exists(mcperf_file) or not os.path.exists(pods_file):
        print(f"Missing files for run {run_number}. Skipping.")
        return

    mcperf_data = parse_mcperf_data(mcperf_file)
    pod_info, earliest_job_start_ms = process_pods_file(pods_file)

    if not mcperf_data or not pod_info:
        print(f"No data found for run {run_number}. Skipping.")
        return

    # Print some debug info
    print(
        f"Run {run_number}: Found {len(mcperf_data)} mcperf data points and {len(pod_info)} jobs"
    )

    # Debug: Print time ranges to check for overlap
    if mcperf_data:
        mcperf_start = min(d[0] for d in mcperf_data)
        mcperf_end = max(d[1] for d in mcperf_data)
        print(f"  mcperf time range (after correction): {mcperf_start} to {mcperf_end}")

    if pod_info:
        pod_start = min(info["start_ms"] for info in pod_info.values())
        pod_end = max(info["end_ms"] for info in pod_info.values())
        print(f"  pod time range: {pod_start} to {pod_end}")

    # Create a new figure
    plt.figure(figsize=(14, 8))
    plt.style.use("ggplot")

    # Use a line plot instead of bars for p95 latency
    x_points, y_points = [], []

    for ts_start_ms, ts_end_ms, p95 in mcperf_data:
        # Calculate the midpoint of each measurement interval
        ts_mid_ms = (ts_start_ms + ts_end_ms) / 2
        # Convert to seconds relative to the first job start
        rel_mid_sec = (ts_mid_ms - earliest_job_start_ms) / 1000

        # Store the data points for plotting
        x_points.append(rel_mid_sec)
        y_points.append(p95)

    # Sort points by x-value for proper line connection
    if x_points:
        sorted_points = sorted(zip(x_points, y_points))
        x_points = [p[0] for p in sorted_points]
        y_points = [p[1] for p in sorted_points]

        # Plot the p95 latency line with markers
        plt.plot(
            x_points,
            y_points,
            color="#3080A0",
            linestyle="-",
            linewidth=2.5,
            marker="o",
            markersize=6,
            markerfacecolor="#3080A0",
            alpha=0.9,
            label="Memcached p95 latency",
            zorder=10,
        )

    # Calculate staggered y-positions for job labels to avoid overlap
    job_count = len(pod_info)
    y_positions = {}

    # First, sort jobs by start time
    sorted_jobs = sorted(pod_info.items(), key=lambda x: x[1]["start_ms"])

    # Assign staggered y-positions - use a wider range
    for i, (job_name, _) in enumerate(sorted_jobs):
        # Create staggered positions between 300 and 900 μs
        y_positions[job_name] = 500 + (i * 100) % 600

    # Used to track unique jobs for the legend
    seen_jobs = set()
    legend_elements = []

    # Add job annotations
    for job_name, info in sorted_jobs:
        # Convert to seconds for the plot
        rel_start_sec = (info["start_ms"] - earliest_job_start_ms) / 1000
        rel_end_sec = (info["end_ms"] - earliest_job_start_ms) / 1000
        job_duration_sec = rel_end_sec - rel_start_sec

        color = JOB_COLORS.get(job_name, "white")  # Default to white if not found
        short_name = job_name.replace("parsec-", "")

        # Format node name nicely if possible
        node_display = NODE_NAMES.get(info["node"], info["node"])

        # Add colored background for job duration
        plt.axvspan(rel_start_sec, rel_end_sec, color=color, alpha=0.2, zorder=1)

        # Add vertical lines for start and end times
        plt.axvline(
            x=rel_start_sec,
            color=color,
            linestyle="-.",
            alpha=0.9,
            zorder=2,
            linewidth=2.5,
        )
        plt.axvline(
            x=rel_end_sec,
            color=color,
            linestyle="-.",
            alpha=0.9,
            zorder=2,
            linewidth=2.5,
        )

        # Use the pre-calculated y-position to avoid overlaps
        y_pos = y_positions[job_name]

        # Add text annotation with job name and node - place in the middle if job is wide enough
        if (
            job_duration_sec >= 5
        ):  # If job is at least 5 seconds long, place text in middle
            mid_point = (rel_start_sec + rel_end_sec) / 2
            plt.text(
                mid_point,
                y_pos,
                f"{short_name}\n({node_display})",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                bbox=dict(
                    facecolor="white",
                    alpha=0.9,
                    boxstyle="round,pad=0.3",
                    edgecolor=color,
                    linewidth=2,
                ),
            )
        else:  # For short jobs, place text above the end marker with a pointer
            plt.text(
                rel_end_sec + 1,
                y_pos,
                f"{short_name}\n({node_display})",
                ha="left",
                va="center",
                fontsize=9,
                fontweight="bold",
                bbox=dict(
                    facecolor="white",
                    alpha=0.9,
                    boxstyle="round,pad=1",
                    edgecolor=color,
                    linewidth=2,
                ),
            )
            # Add an arrow pointing to the job
            plt.annotate(
                "",
                xy=(rel_end_sec, y_pos),
                xytext=(rel_end_sec + 0.9, y_pos),
                arrowprops=dict(arrowstyle="->", color=color, linewidth=1.5),
            )

        # Add to legend if we haven't seen this job type before
        if short_name not in seen_jobs:
            seen_jobs.add(short_name)
            legend_elements.append(Patch(facecolor=color, alpha=0.5, label=short_name))

    # Add SLO threshold line
    plt.axhline(y=1000, color="r", linestyle="-", linewidth=1.5)
    legend_elements.append(
        Line2D(
            [0],
            [0],
            color="red",
            linestyle="-",
            linewidth=1.5,
            label="SLO Threshold (1ms)",
        )
    )

    # Add p95 latency to legend
    legend_elements.append(
        Line2D(
            [0],
            [0],
            color="#3080A0",
            linestyle="-",
            linewidth=2.5,
            marker="o",
            markersize=6,
            label="p95 latency",
        )
    )

    # Set labels and title
    plt.xlabel("Time Since First Job Start (seconds)", fontsize=12)
    plt.ylabel("p95 Latency (μs)", fontsize=12)
    plt.title(
        f"Run #{run_number}: Memcached p95 Latency with Batch Job Activity", fontsize=14
    )

    # Set y-axis limit to 1.6ms to show SLO violations clearly
    plt.ylim(0, 1600)

    # Set x-axis limits
    if x_points:
        min_x = min(-5, min(x_points) - 5)  # Show at most 5 seconds before first job
        max_x = max(
            60,
            max(
                [
                    (info["end_ms"] - earliest_job_start_ms) / 1000
                    for info in pod_info.values()
                ]
            )
            + 15,
        )
        plt.xlim(min_x, max_x)

        # Add a vertical line at x=0 to highlight the first job start
        plt.axvline(
            x=0, color="black", linestyle=":", linewidth=1.0, alpha=0.6, zorder=0
        )
        plt.text(
            0,
            100,
            "First Job Start",
            ha="center",
            va="bottom",
            fontsize=8,
            bbox=dict(facecolor="white", alpha=0.8, boxstyle="round,pad=0.5", edgecolor="black",
                    linewidth=2),
        )

    # Add grid for better readability
    plt.grid(True, linestyle="--", alpha=0.3)

    # Add legend with proper formatting
    plt.legend(
        handles=legend_elements,
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=9,
        framealpha=0.7,
    )

    # Save and close the figure
    plt.tight_layout()
    output_path = f"memcached_latency_run_{run_number}.png"
    plt.savefig(output_path, dpi=1000, bbox_inches="tight")
    plt.close()

    print(f"Created p95 latency plot for run {run_number} -> {output_path}")

    # Print summary statistics
    if y_points:
        slo_violations = sum(1 for p95 in y_points if p95 > 1000.0)  # > 1000 μs = > 1ms

        print(f"  Total measurements: {len(y_points)}")
        print(
            f"  SLO violations (>1ms): {slo_violations} ({slo_violations/len(y_points)*100:.1f}%)"
        )
        print(
            f"  Min/Avg/Max p95 latency: {min(y_points):.1f}/{np.mean(y_points):.1f}/{max(y_points):.1f} μs"
        )


# Run the visualization for all three runs
for run in [1, 2, 3]:
    print(f"\nProcessing run {run}...")
    create_plots(run)

print("\nAll plots created successfully!")
