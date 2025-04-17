import subprocess
import yaml
import time
import os

# start memcached server with C Cores and T threads

experiments = {
    "1": {
        "Cores": "0",
        "Threads": 1
    },
    "2": { 
        "Cores": "0,1",
        "Threads": 1
    },
    "3": {
        "Cores": "0",
        "Threads": 2
    },
    "4": {
        "Cores": "0,1",
        "Threads": 2
    }
}

def run_load(path: str):
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



        # memcached_internal_ip = inventory["all"]["children"]["memcached_servers"]["hosts"]["memcache-server"]["ansible_host"]
        # client_agent_internal_ip = inventory["all"]["children"]["client_agents"]["hosts"]["client-agent"]["internal_ip"]

        # print(f"load data into memcached")
        # subprocess.run([
        #     "ssh",
        #     "-i", "~/.ssh/cloud-computing",
        #     f"ubuntu@{client_measure_external_ip}",
        #     "cd memcache-perf-dynamic && ./mcperf -s 10.0.16.6 --loadonly"
        # ], check=True)

        # time.sleep(10)

        # print(f"running load")

        # with open(path, "w") as f:
        #     # run the load and save the output to the path
        #     subprocess.run([
        #         "ssh",
        #     "-i", "~/.ssh/cloud-computing",
        #     f"ubuntu@{client_measure_external_ip}",
        #     f"cd memcache-perf-dynamic && ./mcperf -s {memcached_internal_ip} -a {client_agent_internal_ip} --noload -T 8 -C 8 -D 4 -Q 1000 -c 8 -t 5 --scan 5000:220000:5000"
        #     ], check=True,
        #     stdout=f,
        #     stderr=f
        # )

       


def run_experiment(experiment: str, run: int = 1, output_dir: str = "output"):
    print(f"running experiment {experiment} with run {run}")
    with open("ansible/inventory.yaml", "r") as f:
        inventory = yaml.safe_load(f)
        memcached_external_ip = inventory["all"]["children"]["memcached_servers"]["hosts"]["memcache-server"]["ansible_host"]
        memcached_internal_ip = inventory["all"]["children"]["memcached_servers"]["hosts"]["memcache-server"]["internal_ip"]
        
        print(f"stopping memcached")
        # stop memcached
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{memcached_external_ip}",
            "sudo systemctl stop memcached"
        ], check=True)

        print(f"killing any remaining memcached processes")
        # kill any remaining memcached processes
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{memcached_external_ip}",
            "sudo pkill -f memcached"
        ], check=True)
        time.sleep(5)

        print(f"starting memcached")
        # start memcached with correct command structure
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{memcached_external_ip}",
            f"sudo taskset -c {experiments[experiment]['Cores']} memcached -d -t {experiments[experiment]['Threads']} -m 1024 -p 11211 -l {memcached_internal_ip} -u memcache"
        ], check=True)
        
        print(f"waiting for 10 seconds")
        time.sleep(10)

        print(f"running load")
        # run the load 
        run_load(f"{output_dir}/experiment{experiment}_run{run}.txt")
        print(f"load finished")

        print(f"stopping memcached")
        # stop memcached
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{memcached_external_ip}",
            "sudo systemctl stop memcached"
        ], check=True)

        print(f"killing any remaining memcached processes")
        # kill any remaining memcached processes
        subprocess.run([
            "ssh",
            "-i", "~/.ssh/cloud-computing",
            f"ubuntu@{memcached_external_ip}",
            "sudo pkill -f memcached"
        ], check=True)
        time.sleep(5)



if __name__ == "__main__":
    for experiment in experiments:
        for run in range(0, 3):
            path = f"output/experiment{experiment}_run{run}.txt"
            if os.path.exists(path):
                print(f"skipping {path} because it already exists")
                continue
            run_experiment(experiment, run)



