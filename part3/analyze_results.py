#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import json
from datetime import datetime
import os
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Define colors (from LaTeX)
JOB_COLORS = {
    "parsec-blackscholes": "#CCA000",
    "parsec-canneal": "#CCCCAA",
    "parsec-dedup": "#CCACCA",
    "parsec-ferret": "#AACCCA",
    "parsec-freqmine": "#0CCA00",
    "parsec-radix": "#00CCA0",
    "parsec-vips": "#CC0A00",
}

# Define human-readable node names
NODE_NAMES = {
    "a": "node-a-2core",
    "b": "node-b-2core",
    "c": "node-c-4core",
    "d": "node-d-4core (memcached)",
}


def parse_mcperf_data(file_path):
    data = []
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split()
            if parts[0] == "read" and len(parts) >= 16:
                ts_start = int(parts[-2]) / 1000  # Convert to seconds
                ts_end = int(parts[-1]) / 1000  # Convert to seconds
                p95 = float(parts[12])  # p95 latency in microseconds
                data.append((ts_start, ts_end, p95))
    return data


def parse_pod_data(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)

    job_info = {}
    for item in data["items"]:
        try:
            name = item["metadata"]["name"]
            job_name = "-".join(name.split("-")[:-1]) if "-" in name else name

            if job_name == "memcached":
                continue

            if "containerStatuses" in item["status"]:
                container_status = item["status"]["containerStatuses"][0]
                if (
                    "state" in container_status
                    and "terminated" in container_status["state"]
                ):
                    terminated = container_status["state"]["terminated"]

                    # Parse timestamps (both already in UTC)
                    start_time = datetime.strptime(
                        terminated["startedAt"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    end_time = datetime.strptime(
                        terminated["finishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                    )

                    # Convert to timestamp in seconds since epoch
                    start_ts = start_time.timestamp()
                    end_ts = end_time.timestamp()

                    # Get node name (machine)
                    node_name = item["spec"].get("nodeName", "unknown")
                    short_node = (
                        node_name.split("-")[-1] if "-" in node_name else node_name
                    )

                    # Get human-readable node name
                    readable_node = NODE_NAMES.get(short_node, short_node)

                    job_info[job_name] = {
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "node": short_node,
                        "readable_node": readable_node,
                    }
        except Exception as e:
            print(f"Error processing pod: {e}")

    return job_info


def create_plots(run_number):
    mcperf_file = f"part_3_results_group_020/mcperf_{run_number}.txt"
    pods_file = f"part_3_results_group_020/pods_{run_number}.json"

    if not os.path.exists(mcperf_file) or not os.path.exists(pods_file):
        print(f"Missing files for run {run_number}. Skipping.")
        return

    mcperf_data = parse_mcperf_data(mcperf_file)
    pod_info = parse_pod_data(pods_file)

    if not mcperf_data or not pod_info:
        print(f"No data found for run {run_number}. Skipping.")
        return

    job_start_times = [info["start_ts"] for info in pod_info.values()]
    earliest_job_start = min(job_start_times)

    # REMOVE THE TIMEZONE OFFSET - both timestamps are already in UTC
    # timezone_offset = 7200  # This was the issue!

    plt.figure(figsize=(12, 6))
    plt.style.use("ggplot")

    x_points, y_points = [], []
    for ts_start, ts_end, p95 in mcperf_data:
        # Remove the timezone offset adjustment
        rel_mid = ((ts_start + ts_end) / 2) - earliest_job_start
        if rel_mid > -30:  # Keep some buffer for visualization
            x_points.append(rel_mid)
            y_points.append(p95)

    # Plot the memcached latency data
    latency_line = plt.plot(
        x_points,
        y_points,
        "-o",
        markersize=3,
        alpha=0.7,
        color="#3080A0",
        label="p95 latency",
    )[0]

    # Used to track unique jobs for the legend
    seen_jobs = set()
    legend_elements = []

    for job_name, info in sorted(pod_info.items(), key=lambda x: x[1]["start_ts"]):
        rel_start = info["start_ts"] - earliest_job_start
        rel_end = info["end_ts"] - earliest_job_start
        duration = rel_end - rel_start
        color = JOB_COLORS.get(job_name, "gray")
        short_name = job_name.replace("parsec-", "")

        plt.axvspan(rel_start, rel_end, color=color, alpha=0.15, zorder=1)
        plt.axvline(x=rel_start, color=color, linestyle="--", alpha=0.5, zorder=2)
        plt.axvline(x=rel_end, color=color, linestyle="--", alpha=0.5, zorder=2)

        # Add text annotation with readable node name
        plt.text(
            (rel_start + rel_end) / 2,
            plt.ylim()[1] * 0.95,
            f"{short_name}\n({info['readable_node']})",
            ha="center",
            va="top",
            fontsize=8,
            bbox=dict(
                facecolor="white",
                alpha=0.7,
                boxstyle="round,pad=0.2",
                edgecolor=color,
                linewidth=1.5,
            ),
        )

        if short_name not in seen_jobs:
            seen_jobs.add(short_name)
            legend_elements.append(
                Patch(
                    facecolor=color,
                    alpha=0.3,
                    label=f"{short_name} ({info['readable_node']})",
                )
            )

    # Add SLO threshold line
    slo_line = plt.axhline(y=1000, color="r", linestyle="-", linewidth=1.5)

    plt.xlabel("Time Since First Job Start (seconds)", fontsize=10)
    plt.ylabel("p95 Latency (μs)", fontsize=10)
    plt.title(
        f"Run #{run_number}: Memcached p95 Latency with Batch Job Activity", fontsize=12
    )

    max_latency = max(y_points) if y_points else 1200
    plt.ylim(0, min(max_latency * 1.2, 1200))

    plt.xlim(
        min(x_points) - 5 if x_points else -5,
        max([info["end_ts"] - earliest_job_start for info in pod_info.values()]) + 5,
    )

    plt.grid(True, linestyle="--", alpha=0.3)

    # Fix the legend to show the latency line and SLO threshold properly
    plt.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color="#3080A0",
                marker="o",
                linewidth=1,
                markersize=3,
                label="Memcached p95 latency",
            ),
            Line2D(
                [0],
                [0],
                color="r",
                linestyle="-",
                linewidth=1.5,
                label="SLO Threshold (1ms)",
            ),
        ]
        + legend_elements,
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
        framealpha=0.7,
    )

    plt.tight_layout()
    plt.savefig(f"memcached_latency_run_{run_number}.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Created plot for run {run_number} (with fixed UTC timestamps)")


for run in [1, 2, 3]:
    create_plots(run)

print("Plots created successfully with correct timestamp alignment!")
