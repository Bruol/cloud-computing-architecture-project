#! /usr/bin/env python3

import subprocess
import psutil
import time
from typing import Dict
from policy_1_2_cores import Policy1And2Cores
from job import JobInfo
import logging


logger = logging.getLogger(__name__)

CPU_LOW = 75
CPU_HIGH = 140

jobs: Dict[str, JobInfo] = {
    "blackscholes": {
        "image": "anakli/cca:parsec_blackscholes",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p blackscholes -i native -n {threads}"],
    },
    "canneal": {
        "image": "anakli/cca:parsec_canneal", 
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p canneal -i native -n {threads}"],
    },
    "dedup": {
        "image": "anakli/cca:parsec_dedup",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p dedup -i native -n {threads}"],
    },
    "ferret": {
        "image": "anakli/cca:parsec_ferret",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p ferret -i native -n {threads}"],
    },
    "freqmine": {
        "image": "anakli/cca:parsec_freqmine",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p freqmine -i native -n {threads}"],
    },
    "radix": {
        "image": "anakli/cca:splash2x_radix",
        "command": ["/bin/sh", "-c", "./run -a run -S splash2x -p radix -i native -n {threads}"],
    },
    "vips": {
        "image": "anakli/cca:parsec_vips",
        "command": ["/bin/sh", "-c", "./run -a run -S parsec -p vips -i native -n {threads}"],
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




def main():
    # log to a file (scheduler_04052025_17h36.log) with epoch time
    logging.basicConfig(level=logging.INFO, format=f"{time.time()} -- %(message)s", filename=f"scheduler_{time.strftime('%d%m%Y_%H%M')}.log")

    memcached_pid = get_memcached_pid()
    logger.info(f"Memcached PID: {memcached_pid}")
    memcached_target_cores = 1
    set_memcached_cpu_affinity(memcached_pid, "0")
    logger.info(f"Memcached CPU affinity set to 0")

    # Initialize policies
    policy_1_2 = Policy1And2Cores()
    
    
    while True:
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)

        if memcached_target_cores == 1 and cpu_usage[0] > CPU_LOW:
            memcached_target_cores = 2
        elif memcached_target_cores == 2 and cpu_usage[0] + cpu_usage[1] < CPU_HIGH:
            memcached_target_cores = 1
       

        # TODO: log events for later analysis
        # TODO: start jobs
        # TODO: change the cpu affinity of the memcached process as neccessary
        # TODO: pause jobs
        # TODO: unpause jobs
        # TODO: check if the jobs are done



if __name__ == "__main__":
    main()
