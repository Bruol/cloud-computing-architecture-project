#! /usr/bin/env python3

import subprocess
import psutil
import time
from typing import Dict
from policy_1_2_cores import Policy1And2Cores
from policy_2_3_cores import Policy2And3Cores
from job import JobInfo
from policy import Policy
import logging
import sys
from colorama import init, Fore, Style

# Initialize colorama
init()

# Custom formatter with colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            record.levelname = f"{Fore.GREEN}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            record.levelname = f"{Fore.YELLOW}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            record.levelname = f"{Fore.RED}{record.levelname}{Style.RESET_ALL}"
        elif record.levelno == logging.DEBUG:
            record.levelname = f"{Fore.BLUE}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

logger = logging.getLogger(__name__)

CPU_LOW = 75
CPU_HIGH = 140

jobs: Dict[str, JobInfo] = {
    "blackscholes": {
        "name": "blackscholes",
        "image": "anakli/cca:parsec_blackscholes",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p blackscholes -i native -n {threads}"],
        "paralellizability": 1,
    },
    "canneal": {
        "name": "canneal",
        "image": "anakli/cca:parsec_canneal", 
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p canneal -i native -n {threads}"],
        "paralellizability": 1,
    },
    "dedup": {
        "name": "dedup",
        "image": "anakli/cca:parsec_dedup",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p dedup -i native -n {threads}"],
        "paralellizability": 1,
    },
    "ferret": {
        "name": "ferret",
        "image": "anakli/cca:parsec_ferret",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p ferret -i native -n {threads}"],
        "paralellizability": 2,
    },
    "freqmine": {
        "name": "freqmine",
        "image": "anakli/cca:parsec_freqmine",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p freqmine -i native -n {threads}"],
        "paralellizability": 2,
    },
    "radix": {
        "name": "radix",
        "image": "anakli/cca:splash2x_radix",
        "command": ["/bin/sh", "-c", "./run -a run -S splash2x -p radix -i native -n {threads}"],
        "paralellizability": 2,
    },
    "vips": {
        "name": "vips",
        "image": "anakli/cca:parsec_vips",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p vips -i native -n {threads}"],
        "paralellizability": 2,
    },
}


# TODO: test this
def get_memcached_pid():
    # get the pid of the memcached process
    return subprocess.check_output(["pgrep", "-f", "memcached"]).decode("utf-8").strip()

# TODO: test this
def set_memcached_cpu_affinity(pid: int, cores: str):
    # set the cpu affinity of the memcached process
    # taskset -a -p <pid> -c <cores>
    subprocess.run(["taskset", "-a", "-p", str(pid), "-c", cores])
        

# create two policies. 
# 1) One has 2 and 3 core jobs. It maintains 2 queues to run 2 and 3 core jobs.
        # when three cores are available it will start/resume the first job in the 3 core queue and pause the 2 core job currently running
        # when two cores are available it will start/resume the first job in the 2 core queue and pause the 3 core job currently running
        # if 
# 2) The other has 1 and 2 core jobs. It maintains 2 queues to run the jobs.
        # it will run the 2 core jobs sequentially.
        # it will run the 1 core if a 3rd core is available. 
        # If there are no 2 core jobs left, it will run the 1 core jobs on the remaining cores. 
        # If no more 1 core jobs are left, it will run the 2 core jobs on all available cores.




def main(policy: Policy):
    # log to a file (scheduler_04052025_17h36.log) with epoch time
    formatter = ColoredFormatter(f"[{time.time()}] [policy: {policy.policy_name}] [%(levelname)s] [%(name)s] %(message)s")
    
    # File handler without colors
    file_handler = logging.FileHandler(f"scheduler_{time.strftime('%d%m%Y_%H%M')}.log")
    file_handler.setFormatter(logging.Formatter(f"[{time.time()}] [policy: {policy.policy_name}] [%(levelname)s] [%(name)s] %(message)s"))
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    #memcached_pid = get_memcached_pid()
    #logger.info(f"Memcached PID: {memcached_pid}")
    memcached_target_cores = 0
    #set_memcached_cpu_affinity(memcached_pid, "0")
    #logger.info(f"Memcached CPU affinity set to 0")

    for job in jobs:
        policy.add_job(jobs[job])

    logger.info(f"Starting scheduler with policy: {policy.policy_name}")

    start_time = time.time()

    while True:
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)

        logger.info(f"CPU usage: {cpu_usage}")

        if memcached_target_cores == 1 and cpu_usage[0] > CPU_LOW:
            memcached_target_cores = 2
        elif memcached_target_cores == 2 and cpu_usage[0] + cpu_usage[1] < CPU_HIGH:
            memcached_target_cores = 1
       

        available_cores = set(range(len(cpu_usage)))-set(range(memcached_target_cores))
        
        logger.info(f"Available cores: {available_cores}")

        policy.schedule(available_cores)

        if policy.isCompleted:
            break
    
        time.sleep(1)


    end_time = time.time()
    logger.info(f"Scheduler completed in {end_time - start_time} seconds")


if __name__ == "__main__":
    
    # Initialize policies
    policy1 = Policy1And2Cores()
    policy2 = Policy2And3Cores()

    main(policy1)

    main(policy2)
