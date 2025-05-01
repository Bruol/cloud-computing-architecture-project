#! /usr/bin/env python3

import subprocess
import psutil
import docker
import time

jobs = {
    "blackscholes": {
        "image": "anakli/cca:parsec_blackscholes",
    },
    "canneal": {
        "image": "anakli/cca:parsec_canneal",
    },
    "dedup": {
        "image": "anakli/cca:parsec_dedup",
    },
    "ferret": {
        "image": "anakli/cca:parsec_ferret",
    },
    "radix": {
        "image": "anakli/cca:splash2x_radix",
    },
    "vips": {
        "image": "anakli/cca:parsec_vips",
    },
}

docker_client = docker.from_env()

def get_memcached_pid():
    # get the pid of the memcached process
    return subprocess.check_output(["pgrep", "-f", "memcached"]).decode("utf-8").strip()


def set_memcached_cpu_affinity(pid: int, cores: str):
    # set the cpu affinity of the memcached process
    # taskset -a -p <pid> -c <cores>
    subprocess.run(["taskset", "-a", "-p", str(pid), "-c", cores])


def start_job(job: str, cores: str, threads: str):
    # return the container
    # docker run --cpuset-cpus="0" -d --rm --name parsec anakli/cca:parsec_blackscholes ./run -a run -S parsec -p blackscholes -i native -n 2
    container = docker_client.containers.run(
        jobs[job]["image"],
        f"run -a run -S parsec -p {job} -i native -n {threads}",
        cpuset_cpus=cores,
        name=f"parsec-{job}",
        remove=True,
    )
    return container


def main():
    memcached_pid = get_memcached_pid()
    print(f"{time.time()} -- Memcached PID: {memcached_pid}")
    set_memcached_cpu_affinity(memcached_pid, "0")
    print(f"{time.time()} -- Memcached CPU affinity set to 0")

    while True:
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)
        
        # start jobs
        # change the cpu affinity of the memcached process as neccessary
        # pause jobs
        # unpause jobs
        # check if the jobs are done



if __name__ == "__main__":
    main()
