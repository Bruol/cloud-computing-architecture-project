import subprocess
import yaml
import time
import os
import sys
from datetime import datetime

# Define the policies to test
POLICIES = {
    "policy1": "1",  # Policy1And2Cores
    "policy2": "2"   # Policy2And3Cores
}

def run_load(path: str):
    """Run the load test and save output to the specified path."""
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open("ansible/inventory.yaml", "r") as f:
        inventory = yaml.safe_load(f)
        client_measure_external_ip = inventory["all"]["children"]["client_measures"]["hosts"]["client-measure"]["ansible_host"]

        with open(path, "w") as f:
            # run the load and save the output to the path
            subprocess.run([
                "ssh",
                "-i", "~/.ssh/cloud-computing",
                f"ubuntu@{client_measure_external_ip}",
                "cd memcache-perf-dynamic && ./run_load.sh"
            ], check=True,
            stdout=f,
            stderr=f
            )

def run_experiment(policy: str, run: int = 1, output_dir: str = "part4_2_logs"):
    """Run a single experiment with the specified policy."""
    print(f"[{datetime.now()}] Running experiment with policy {policy}, run {run}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    with open("ansible/inventory.yaml", "r") as f:
        inventory = yaml.safe_load(f)
        
        # Start the scheduler with the specified policy
        scheduler_log = f"scheduler_policy{policy}_run{run}.log"
        print(f"[{datetime.now()}] Starting scheduler with policy {policy}")
        
        scheduler_process = subprocess.Popen([
            "ssh",
            "-i", "~/.ssh/cloud-computing", 
            f"ubuntu@{inventory['all']['children']['memcached_servers']['hosts']['memcache-server']['ansible_host']}", 
            f"cd ~/scheduler && venv/bin/python3 main.py -p {policy} -l {scheduler_log}"
        ])
        
        # Wait for scheduler to initialize
        time.sleep(5)
        
        # Run the load test
        mcperf_log = os.path.join(output_dir, f"mcperf_policy{policy}_run{run}.txt")
        print(f"[{datetime.now()}] Starting mcperf load test")
        run_load(mcperf_log)
        
        # Wait for a bit to ensure all data is collected
        time.sleep(5)
        
        # Stop the scheduler
        print(f"[{datetime.now()}] Stopping scheduler")
        scheduler_process.terminate()
        scheduler_process.wait()

        # copy the scheduler log to the output directory
        subprocess.run([
            "scp",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{inventory['all']['children']['memcached_servers']['hosts']['memcache-server']['ansible_host']}:~/scheduler/{scheduler_log}",
            output_dir
        ])
        
        print(f"[{datetime.now()}] Experiment completed. Logs saved to {output_dir}")

def main():
    """Main function to run all experiments."""
    # Number of runs per policy
    NUM_RUNS = 3
    
    # Run each policy multiple times
    for policy_name, policy_value in POLICIES.items():
        print(f"\n=== Starting experiments for {policy_name} ===")
        for run in range(NUM_RUNS):
            run_experiment(policy_value, run + 1)
            # Wait between runs
            if run < NUM_RUNS - 1:
                print(f"Waiting 60 seconds before next run...")
                time.sleep(60)
    
    print("\n=== All experiments completed ===")

if __name__ == "__main__":
    main()
