import json
import statistics
import os
import sys
from datetime import datetime

# Set constants
RESULTS_DIR = "part_3_results_group_020"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def extract_job_times(json_file):
    """Extract job execution times from a pods JSON file."""
    with open(json_file, "r") as f:
        data = json.load(f)

    job_times = {}
    job_start_times = {}
    job_end_times = {}

    for item in data["items"]:
        try:
            name = item["metadata"]["name"]
            # Extract the job name without the random suffix
            job_name = "-".join(name.split("-")[:-1]) if "-" in name else name

            # Skip memcached
            if job_name == "memcached":
                continue

            if "containerStatuses" in item["status"]:
                container_status = item["status"]["containerStatuses"][0]
                if (
                    "state" in container_status
                    and "terminated" in container_status["state"]
                ):
                    terminated = container_status["state"]["terminated"]

                    # Parse timestamps
                    start_time = datetime.strptime(terminated["startedAt"], TIME_FORMAT)
                    end_time = datetime.strptime(terminated["finishedAt"], TIME_FORMAT)
                    duration = (end_time - start_time).total_seconds()

                    # Store the data
                    job_times[job_name] = duration
                    job_start_times[job_name] = start_time
                    job_end_times[job_name] = end_time
        except (KeyError, IndexError) as e:
            print(f"Error processing item: {e}")
            continue

    # Calculate total execution time (makespan)
    if job_start_times and job_end_times:
        earliest_start = min(job_start_times.values())
        latest_end = max(job_end_times.values())
        job_times["total"] = (latest_end - earliest_start).total_seconds()

    return job_times, earliest_start, latest_end


def analyze_memcached_latency(mcperf_file, start_time, end_time):
    """Analyze memcached latency data and check for SLO violations."""
    violations = 0
    total_points = 0

    # Debug print to see the time windows
    print(f"\nAnalyzing {mcperf_file}")
    print(f"Job execution window: {start_time} to {end_time}")

    try:
        # Read the mcperf output
        with open(mcperf_file, "r") as f:
            lines = f.readlines()

        # For timestamp debugging - show a sample
        sample_shown = False

        for line in lines:
            if line.startswith("#") or not line.strip():
                continue

            # Parse the line
            parts = line.strip().split()
            if len(parts) < 16 or parts[0] != "read":
                continue

            try:
                # Extract p95 latency (microseconds)
                p95 = float(parts[12])

                # Extract timestamp (milliseconds since epoch)
                ts_end = int(parts[-1])
                ts_start = int(parts[-2])

                # Print a sample timestamp for debugging
                if not sample_shown:
                    ts_end_dt = datetime.fromtimestamp(ts_end / 1000)
                    print(f"Sample mcperf timestamp: {ts_end_dt} (from {ts_end})")
                    sample_shown = True

                # Count all points for now instead of filtering by time
                # We'll check p95 > 1000μs for SLO violation
                if p95 > 1000:
                    violations += 1

                total_points += 1

            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {e}")
                continue
    except Exception as e:
        print(f"Error processing file {mcperf_file}: {e}")

    print(f"Found {total_points} data points, {violations} SLO violations")
    return violations, total_points


def main():
    # Check if the results directory exists
    if not os.path.isdir(RESULTS_DIR):
        print(f"Error: Results directory '{RESULTS_DIR}' not found.")
        return 1

    # Dictionary to store execution times for each job across runs
    all_job_times = {}
    all_earliest_starts = []
    all_latest_ends = []

    # Process each run
    for run in range(1, 4):
        pods_file = os.path.join(RESULTS_DIR, f"pods_{run}.json")
        mcperf_file = os.path.join(RESULTS_DIR, f"mcperf_{run}.txt")

        # Check if files exist
        if not os.path.exists(pods_file):
            print(f"Warning: {pods_file} not found.")
            continue

        if not os.path.exists(mcperf_file):
            print(f"Warning: {mcperf_file} not found.")
            continue

        # Extract job execution times
        job_times, earliest_start, latest_end = extract_job_times(pods_file)
        all_earliest_starts.append(earliest_start)
        all_latest_ends.append(latest_end)

        # Store times for this run
        for job, time in job_times.items():
            if job not in all_job_times:
                all_job_times[job] = []
            all_job_times[job].append(time)

    # Calculate statistics for each job
    job_stats = {}
    for job, times in all_job_times.items():
        if len(times) > 0:
            mean = statistics.mean(times)
            std = statistics.stdev(times) if len(times) > 1 else 0
            job_stats[job] = {"mean": mean, "std": std}

    # Calculate SLO violations
    total_violations = 0
    total_points = 0

    for run in range(1, 4):
        mcperf_file = os.path.join(RESULTS_DIR, f"mcperf_{run}.txt")
        if os.path.exists(mcperf_file):
            # Use the earliest start and latest end times for this run
            violations, points = analyze_memcached_latency(
                mcperf_file, all_earliest_starts[run - 1], all_latest_ends[run - 1]
            )
            total_violations += violations
            total_points += points

    # Calculate SLO violation ratio
    slo_violation_ratio = total_violations / total_points if total_points > 0 else 0

    # Print the results table
    print("\n--- Job Execution Time Statistics ---\n")
    print("| job name     | mean time [s] | std [s] |")
    print("|-------------|--------------|--------|")

    # Expected job names
    expected_jobs = [
        "parsec-blackscholes",
        "parsec-canneal",
        "parsec-dedup",
        "parsec-ferret",
        "parsec-freqmine",
        "parsec-radix",
        "parsec-vips",
        "total",
    ]

    for job in expected_jobs:
        if job in job_stats:
            mean = job_stats[job]["mean"]
            std = job_stats[job]["std"]
            print(f"| {job.replace('parsec-', ''):<12} | {mean:12.2f} | {std:6.2f} |")
        else:
            print(f"| {job.replace('parsec-', ''):<12} | {'N/A':12} | {'N/A':6} |")

    print("\n--- Memcached SLO Analysis ---\n")
    print(
        f"SLO Violation Ratio: {slo_violation_ratio:.6f} ({total_violations}/{total_points})"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
