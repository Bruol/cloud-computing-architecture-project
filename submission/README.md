# Part 3

# Part 4

## set up cluster using ansible

The ansible playbook is in the `part4/ansible` directory.
Here you can find some scripts to measure cpu usage (`cpuUsageMeasurer.py`) and to run the mcperf agent (`mcperf_agent.sh`).
The `set_up_vms.yaml` installs all the necessary packages and sets up the cluster.
The `install_scheduler.yaml` installs the scheduler on the memcached server.
The scheduler can be found in the `part4/scheduler` directory.

part4_x are run on my laptop which uses ssh to start the experiments. The script names are according to the subtask number.

In the `part4/visualization` directory you can find the code to visualize the results and analyze the log files.
