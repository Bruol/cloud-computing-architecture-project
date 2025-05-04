import enum
from typing import Dict, Union
from docker.client import DockerClient
import docker
import logging

logger = logging.getLogger(__name__)

Job = Union[str, list[str]]
JobInfo = Dict[str, Job]

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class JobInstance:
    def __init__(self, jobName: str, image: str, command: list[str], docker_client: DockerClient = docker.from_env()):
        self._jobName = jobName
        self._image = image
        self._command = command
        self._container = None
        self._status = JobStatus.PENDING
        self._docker_client = docker_client

    # TODO: test this
    def start_job(self, cores: str, threads: str):
        # return the container
        # docker run --cpuset-cpus="0" -d --rm --name parsec anakli/cca:parsec_blackscholes ./run -a run -S parsec -p blackscholes -i native -n 2
        
        command = []
        for arg in self._command:
            try:
                command.append(arg.format(threads=threads))
            except:
                command.append(arg)
        
        container = self._docker_client.containers.run(
            self._image,
            command,
            cpuset_cpus=cores,
            name=f"{self._jobName}",
        )

        logger.info(f"Job {self._jobName} started")
        
        self._container = container


    # TODO: test this
    def pause_job(self):
        # pause the job
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")
        self._container.pause()  
        logger.info(f"Job {self._jobName} paused")

    # TODO: test this
    def unpause_job(self):
        # unpause the job
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")
        self._container.unpause()
        logger.info(f"Job {self._jobName} unpaused")

    # TODO: test this
    def update_job_cpus(self, cores: str):
        # update the cpu affinity of the job
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")
        self._container.update_config(cpuset_cpus=cores)
        logger.info(f"Job {self._jobName} updated to {cores} cores")

    # TODO: test this
    def check_job_completed(self):
        # check if the job is completed
        if self._container is None:
            raise ValueError(f"Job {self._jobName} is not running")
        
        container_logs = self._container.logs()

        done = "[PARSEC] Done." in container_logs
        error = "Error" in container_logs

        if done and not error:
            self._status = JobStatus.COMPLETED
        elif error:
            self._status = JobStatus.ERROR
        elif self._container is not None:
            self._status = JobStatus.RUNNING
        else:
            self._status = JobStatus.PENDING
        
        logger.info(f"Job {self._jobName} status: {self._status}")
        
        return self._status
    
