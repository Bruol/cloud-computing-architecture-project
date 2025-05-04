
# Scheduling Policy:
# This policy has 2 and 3 core jobs. It maintains 2 queues to run 2 and 3 core jobs.
# when three cores are available it will start/resume the first job in the 3 core queue and pause the 2 core job currently running
# when two cores are available it will start/resume the first job in the 2 core queue and pause the 3 core job currently running
# if 