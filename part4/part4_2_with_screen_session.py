import subprocess
import yaml
import time
import os
from datetime import datetime

# Define the policies to test
POLICIES = {
    "policy1": "1",  # Policy1And2Cores
    #"policy2": "2"   # Policy2And3Cores
}

def create_screen_session(session_name: str, host: str) -> bool:
    """Create a new screen session on the remote host."""
    try:
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{host}",
            f"screen -dmS {session_name}"
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to create screen session {session_name} on {host}")
        return False

def kill_screen_session(session_name: str, host: str):
    """Kill a screen session on the remote host."""
    try:
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{host}",
            f"screen -X -S {session_name} quit"
        ], check=True)
    except subprocess.CalledProcessError:
        print(f"Failed to kill screen session {session_name} on {host}")

def run_command_in_screen(session_name: str, host: str, command: str) -> bool:
    """Run a command in a screen session on the remote host."""
    try:
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{host}",
            f"screen -S {session_name} -X stuff '{command}\n'"
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to run command in screen session {session_name} on {host}")
        return False

def run_load(logfileName: str):
    """Run the load test and save output to the specified path."""
    with open("ansible/inventory.yaml", "r") as f:
        inventory = yaml.safe_load(f)
        client_measure_external_ip = inventory["all"]["children"]["client_measures"]["hosts"]["client-measure"]["ansible_host"]
    
    # Create a screen session for the load test
    session_name = f"load_test_{int(time.time())}"
    if not create_screen_session(session_name, client_measure_external_ip):
        raise Exception("Failed to create screen session for load test")
    
    # Run the load test in the screen session
    command = f"cd memcache-perf-dynamic && ./run_load.sh {logfileName}"
    if not run_command_in_screen(session_name, client_measure_external_ip, command):
        kill_screen_session(session_name, client_measure_external_ip)
        raise Exception("Failed to start load test in screen session")
    
    return session_name, client_measure_external_ip

def run_experiment(policy: str, run: int = 1, output_dir: str = "part4_2_logs"):
    """Run a single experiment with the specified policy."""
    print(f"[{datetime.now()}] Running experiment with policy {policy}, run {run}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    with open("ansible/inventory.yaml", "r") as f:
        inventory = yaml.safe_load(f)
        server_host = inventory['all']['children']['memcached_servers']['hosts']['memcache-server']['ansible_host']
        client_host = inventory["all"]["children"]["client_measures"]["hosts"]["client-measure"]["ansible_host"]

        try:
            # Run the load test
            mcperf_log = f"mcperf_policy{policy}_run{run}.log"
            print(f"[{datetime.now()}] Starting mcperf load test")
            load_session, load_host = run_load(mcperf_log)
            
            # Wait for a bit to ensure all data is collected
            time.sleep(10)
            
            # Start the scheduler with the specified policy
            scheduler_log = f"scheduler_policy{policy}_run{run}.log"
            print(f"[{datetime.now()}] Starting scheduler with policy {policy}")
            
            # Create a screen session for the scheduler
            scheduler_session = f"scheduler_{int(time.time())}"
            if not create_screen_session(scheduler_session, server_host):
                raise Exception("Failed to create screen session for scheduler")
            
            # Run the scheduler in the screen session
            command = f"cd ~/scheduler && venv/bin/python3 main.py -p {policy} -l {scheduler_log}"
            if not run_command_in_screen(scheduler_session, server_host, command):
                raise Exception("Failed to start scheduler in screen session")
            
            # Wait for the scheduler to complete
            while True:
                try:
                    result = subprocess.run([
                        "ssh",
                        "-i", "~/.ssh/cloud-computing", 
                        f"ubuntu@{server_host}",
                        f"screen -ls | grep {scheduler_session}"
                    ], capture_output=True, text=True)
                    if not result.stdout.strip():
                        break
                    print(f"[{datetime.now()}] Scheduler still running...")
                except subprocess.CalledProcessError:
                    pass
                time.sleep(5)
            
            # Wait for the load test to complete
            while True:
                try:
                    result = subprocess.run([
                        "ssh",
                        "-i", "~/.ssh/cloud-computing",
                        f"ubuntu@{load_host}",
                        f"screen -ls | grep {load_session}"
                    ], capture_output=True, text=True)
                    if not result.stdout.strip():
                        break
                    print(f"[{datetime.now()}] Load test still running...")
                except subprocess.CalledProcessError:
                    pass
                time.sleep(5)

            # Copy the logs
            os.makedirs(output_dir, exist_ok=True)
            
            # Copy scheduler log
            subprocess.run([
                "scp",
                "-i", "~/.ssh/cloud-computing",
                f"ubuntu@{server_host}:~/scheduler/{scheduler_log}",
                output_dir
            ], check=True)

            # copy formatted log
            subprocess.run([
                "scp",
                "-i", "~/.ssh/cloud-computing",
                f"ubuntu@{server_host}:~/scheduler/log.*",
                output_dir
            ], check=True)

            # Copy load test log
            subprocess.run([
                "scp",
                "-i", "~/.ssh/cloud-computing",
                f"ubuntu@{client_host}:~/memcache-perf-dynamic/{mcperf_log}",
                output_dir
            ], check=True)
            
            print(f"[{datetime.now()}] Experiment completed. Logs saved to {output_dir}")
            
        except Exception as e:
            print(f"Error during experiment: {str(e)}")
            # Clean up screen sessions
            try:
                kill_screen_session(load_session, load_host)
            except:
                pass
            try:
                kill_screen_session(scheduler_session, server_host)
            except:
                pass
            raise

def main():
    """Main function to run all experiments."""
    # Number of runs per policy
    NUM_RUNS = 3

    
    # Run each policy multiple times
    for policy_name, policy_value in POLICIES.items():
        print(f"\n=== Starting experiments for {policy_name} ===")
        for run in range(NUM_RUNS):
            if os.path.exists(f"part4_2_logs/scheduler_policy{policy_value}_run{run + 1}.log"):
                print(f"[{datetime.now()}] Experiment {policy_name} run {run + 1} already exists. Skipping...")
                continue
            run_experiment(policy_value, run + 1)
            # Wait between runs
            if run < NUM_RUNS - 1:
                print(f"Waiting 60 seconds before next run...")
                time.sleep(60)
    
    print("\n=== All experiments completed ===")

if __name__ == "__main__":
    main()
