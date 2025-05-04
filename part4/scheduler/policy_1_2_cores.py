# Scheduling Policy:
# This policy has 1 and 2 core jobs. It maintains 2 queues to run the jobs.
# it will run the 2 core jobs sequentially.
# it will run the 1 core if a 3rd core is available. 
# If there are no 2 core jobs left, it will run the 1 core jobs on the remaining cores. 
# If no more 1 core jobs are left, it will run the 2 core jobs on all available cores.

from typing import List, Dict, Optional
from job import JobInstance, JobStatus
import logging
from job import JobInfo
from policy import Policy
logger = logging.getLogger(__name__)


class Policy1And2Cores(Policy):
    def __init__(self):
        self.one_core_queue: List[JobInstance] = []
        self.two_core_queue: List[JobInstance] = []
        self.running_one_core: Optional[JobInstance] = None
        self.running_two_core: Optional[JobInstance] = None
        self.isCompleted = False

    def add_job(self, job: JobInfo):
        """Add a job to the appropriate queue based on its paralellizability."""
        job_instance = JobInstance(job["name"], job["image"], job["command"], 1 if job["paralellizability"] == 1 else 2)
        if job["paralellizability"] == 1:
            self.one_core_queue.append(job_instance)
        elif job["paralellizability"] == 2:
            self.two_core_queue.append(job_instance)


    def schedule(self, available_cores: set[int]):
        """Implement the scheduling policy:
        1. Run 2-core jobs sequentially
        2. Run 1-core jobs if a 3rd core is available
        3. If no 2-core jobs left, run 1-core jobs on remaining cores
        4. If no 1-core jobs left, run 2-core jobs on all available cores
        """
        # Check for completed jobs and free up cores
        self._check_completed_jobs()

        if len(self.one_core_queue) == 0 and len(self.two_core_queue) == 0 and self.running_one_core is None and self.running_two_core is None:
            self.isCompleted = True
            return
        
        # Sort available cores
        sorted_cores = sorted(available_cores)
        
        # If 3 cores available, run both 1-core and 2-core jobs
        if len(available_cores) == 3:
            # If both queues are empty and there's a running job, give it all cores
            if len(self.one_core_queue) == 0 and len(self.two_core_queue) == 0:
                if self.running_one_core is None and self.running_two_core and self.running_two_core._status != JobStatus.COMPLETED:
                    self.running_two_core.update_job_cpus(f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}")
                elif self.running_one_core and self.running_two_core is None and self.running_one_core._status != JobStatus.COMPLETED:
                    self.running_one_core.update_job_cpus(f"{sorted_cores[0]},{sorted_cores[1]},{sorted_cores[2]}")
                return

            # Start/continue 2-core job
            if self.running_two_core is None:
                if len(self.two_core_queue) > 0:
                    self.running_two_core = self.two_core_queue.pop(0)
                    self.running_two_core.start_job(f"{sorted_cores[1]},{sorted_cores[2]}")
                elif len(self.one_core_queue) > 0:
                    # If no 2-core jobs, run a 1-core job on 2 cores
                    self.running_two_core = self.one_core_queue.pop(0) 
                    self.running_two_core.start_job(f"{sorted_cores[1]},{sorted_cores[2]}")
            elif self.running_two_core and self.running_two_core._status == JobStatus.PAUSED:
                self.running_two_core.unpause_job()
            
            # Start 1-core job
            if self.running_one_core is None:
                if len(self.one_core_queue) > 0:
                    self.running_one_core = self.one_core_queue.pop(0)
                    self.running_one_core.start_job(str(sorted_cores[0]))
                elif len(self.two_core_queue) > 0:
                    # If no 1-core jobs, run a 2-core job on 1 core
                    self.running_one_core = self.two_core_queue.pop(0)
                    self.running_one_core.start_job(str(sorted_cores[0]))
            if self.running_one_core and self.running_one_core._status == JobStatus.PAUSED:
                self.running_one_core.unpause_job()
                
        # If 2 cores available, only run 2-core job and pause any running 1-core job
        elif len(available_cores) == 2:
            # If both queues are empty and there's a running job, give it all cores
            if len(self.one_core_queue) == 0 and len(self.two_core_queue) == 0:
                if self.running_one_core is None and self.running_two_core and self.running_two_core._status != JobStatus.COMPLETED:
                    self.running_two_core.update_job_cpus(f"{sorted_cores[0]},{sorted_cores[1]}")
                elif self.running_two_core is None and self.running_one_core and self.running_one_core._status != JobStatus.COMPLETED:
                    self.running_one_core.update_job_cpus(f"{sorted_cores[0]},{sorted_cores[1]}")
                return 

            # Pause running 1-core job if exists
            if self.running_one_core and self.running_one_core._status == JobStatus.RUNNING:
                self.running_one_core.pause_job()
                
            # Start new 2-core job if none running
            if self.running_two_core is None:
                if len(self.two_core_queue) > 0:
                    self.running_two_core = self.two_core_queue.pop(0)
                    self.running_two_core.start_job(f"{sorted_cores[0]},{sorted_cores[1]}")
                elif len(self.one_core_queue) > 0:
                    # If no 2-core jobs, run a 1-core job on 2 cores
                    self.running_two_core = self.one_core_queue.pop(0)
                    self.running_two_core.start_job(f"{sorted_cores[0]},{sorted_cores[1]}")

        return

    def _check_completed_jobs(self):
        """Check for completed jobs and update running jobs accordingly."""
        if self.running_one_core:
            if self.running_one_core.check_job_completed() == JobStatus.COMPLETED:
                logger.info(f"1-core job {self.running_one_core._jobName} completed")
                self.running_one_core = None
            elif self.running_one_core.check_job_completed() == JobStatus.ERROR:
                self.one_core_queue.append(self.running_one_core)
                self.running_one_core = None

        if self.running_two_core:
            if self.running_two_core.check_job_completed() == JobStatus.COMPLETED:
                logger.info(f"2-core job {self.running_two_core._jobName} completed")
                self.running_two_core = None
            elif self.running_two_core.check_job_completed() == JobStatus.ERROR:
                self.two_core_queue.append(self.running_two_core)
                self.running_two_core = None
