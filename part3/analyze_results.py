import json
import numpy as np
import pandas as pd
from datetime import datetime

time_format = "%Y-%m-%dT%H:%M:%SZ"


def extract_job_times(json_file):
    """Extract execution times from a pods json file"""
    with open(json_file, "r") as f:
        data = json.load(f)

    job_times = {}
    start_times = []
    completion_times = []

    for item in data["items"]:
        try:
            name = item["status"]["containerStatuses"][0]["name"]
            if name != "memcached":
                container_status = item["status"]["containerStatuses"][0]["state"]
                if "terminated" in container_status:
                    start_time = datetime.strptime(
                        container_status["terminated"]["startedAt"], time_format
                    )
                    completion_time = datetime.strptime(
                        container_status["terminated"]["finishedAt"], time_format
                    )

                    duration = (completion_time - start_time).total_seconds()
                    job_times[name] = duration
                    start_times.append(start_time)
                    completion_times.append(completion_time)
        except KeyError:
            continue

    if start_times and completion_times:
        makespan = (max(completion_times) - min(start_times)).total_seconds()
        return job_times, makespan
    return job_times, 0


def analyze_mcperf(mcperf_file, start_time, end_time):
    """Analyze mcperf output to find SLO violations during job executions"""
    violations = 0
    total_points = 0

    with open(mcperf_file, "r") as f:
        # Skip header lines
        for _ in range(2):
            next(f)

        for line in f:
            parts = line.strip().split()
            if len(parts) >= 9:  # Ensure we have enough columns
                try:
                    # Assuming columns 7 and 8 have the start/end timestamps
                    measurement_time = float(parts[7])
                    if start_time <= measurement_time <= end_time:
                        p95_latency = float(parts[5])  # 95th percentile latency
                        if p95_latency > 1.0:  # SLO violation if > 1ms
                            violations += 1
                        total_points += 1
                except (ValueError, IndexError):
                    continue

    return violations, total_points


def main():
    runs = 3
    job_data = {}
    makespans = []
    slo_violations = []

    # Process each run
    for run in range(1, runs + 1):
        pods_file = f"pods_{run}.json"
        mcperf_file = f"mcperf_{run}.txt"

        job_times, makespan = extract_job_times(pods_file)
        makespans.append(makespan)

        # Store job times for this run
        for job, time in job_times.items():
            if job not in job_data:
                job_data[job] = []
            job_data[job].append(time)

        # Find start/end times for SLO violation calculation
        with open(pods_file, "r") as f:
            data = json.load(f)

        # Get the time window when batch jobs were running
        all_start_times = []
        all_end_times = []
        for item in data["items"]:
            try:
                name = item["status"]["containerStatuses"][0]["name"]
                if name != "memcached":
                    container_status = item["status"]["containerStatuses"][0]["state"]
                    if "terminated" in container_status:
                        start = datetime.strptime(
                            container_status["terminated"]["startedAt"], time_format
                        ).timestamp()
                        end = datetime.strptime(
                            container_status["terminated"]["finishedAt"], time_format
                        ).timestamp()
                        all_start_times.append(start)
                        all_end_times.append(end)
            except KeyError:
                continue

        if all_start_times and all_end_times:
            start_time = min(all_start_times)
            end_time = max(all_end_times)
            violations, total = analyze_mcperf(mcperf_file, start_time, end_time)
            if total > 0:
                slo_violations.append(violations / total)
            else:
                slo_violations.append(0)

    # Calculate statistics
    print("Job Execution Times (seconds):")
    print("Job Name\tRun 1\tRun 2\tRun 3\tMean\tStd Dev")
    print("-" * 60)

    for job, times in job_data.items():
        if len(times) == runs:
            mean = np.mean(times)
            std = np.std(times)
            print(
                f"{job}\t{times[0]:.2f}\t{times[1]:.2f}\t{times[2]:.2f}\t{mean:.2f}\t{std:.2f}"
            )

    print("\nMakespan (seconds):")
    print("Run 1\tRun 2\tRun 3\tMean\tStd Dev")
    print("-" * 50)
    mean_makespan = np.mean(makespans)
    std_makespan = np.std(makespans)
    print(
        f"{makespans[0]:.2f}\t{makespans[1]:.2f}\t{makespans[2]:.2f}\t{mean_makespan:.2f}\t{std_makespan:.2f}"
    )

    print("\nMemcached SLO Violation Ratio:")
    print("Run 1\tRun 2\tRun 3\tMean\tStd Dev")
    print("-" * 50)
    mean_slo = np.mean(slo_violations)
    std_slo = np.std(slo_violations)
    print(
        f"{slo_violations[0]:.4f}\t{slo_violations[1]:.4f}\t{slo_violations[2]:.4f}\t{mean_slo:.4f}\t{std_slo:.4f}"
    )


if __name__ == "__main__":
    main()
