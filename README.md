# Cloud Computing Architecture Project

This repository contains starter code for the Cloud Computing Architecture course project at ETH Zurich. Students will explore how to schedule latency-sensitive and batch applications in a cloud cluster. Please follow the instructions in the project handout.

## Time-line

Starting from 17 March 2025

1. Week 1 & 2 (17.3. -- 31.3.)
   - Finish Part 1 + 2
2. Week 3 & 4 (31.3. -- 14.4.)
   - Work on Part 3
3. Week 5 - 8 (14.4. -- 12.5.)
   - Work on Part 4
4. Week 9 (12.5. -- 16.5.)
   - Consolidate Results and Final Report

## SSH to K8s cluster

I created a script to ssh to the K8s cluster without typing the long command.
Simply make the ssh-k8s.sh executable and run it. It will display a list of nodes and you can select one.

```bash
chmod +x ssh-k8s.sh
./ssh-k8s.sh
```

**Output:**

```bash
Available nodes:
1. client-agent-wtvv
2. client-measure-9m4h
3. master-europe-west1-b-3c6s
4. memcache-server-59cc
Select a node number to connect to:
```

## Run Part 1

Follow the instructions in the handout and run memcached.

Then run the command bellow to install memperf and load data into memcached.

The `memcached_ip` is hardcoded for now in the script. Keep in mind to replace with updated `ip`

```bash
kubectl get pods -o wide
```

```bash
cd part1
python run_part_1.py install
```

Then run the command bellow to run the client

```bash
python run_part_1.py client
```

Then run the command bellow to run the test suite. Do not stop the client before running this command.

```bash
python run_part_1.py benchmark
```

This will save the logs of the client-measure server in the `part1/logs` folder.

This will run 3 iterations of each interference pattern in

- NONE
- CPU
- L1D
- L1I
- L2
- LLC
- MEMBW

Further the script will wait 60s between each run to ensure a particular run is not influenced by any previous runs. And it will wait until previous pods running interferences are terminated.

## Run Part 2

1. Follow the instructions in the handout and setup the cluster.
2. Keep in mind to change the node type from `memcached` to `parsec` in interference benchmark.
3. Generate the logs for test purposes: `python part2/gen_logs_interference.py --test --workload=canneal --interference=cpu --repetitions=1`
4. Generate all logs: `python part2/gen_logs_interference.py`
5. Visualise the results: `python part2/vis_logs_interference.py part2/parsec_results/all_results.csv --output-dir=part2/visualizations`

## Run Part 3

1. Follow the instructions in the handout and setup the cluster.
2. Install mcperf-dynamic: `./part3/install_mcperf`.sh
3. Run `./part3_experiment.sh <run_number>`
4. Visualise the results: `python3 part3/analyze_results.py`

## Other Information

1. I have one more gcloud account on my machine, so fixing the context issue

```bash
# Create or switch to your intended context
kubectl config set-context part1.k8s.local --cluster=part1.k8s.local

# Use this context
kubectl config use-context part1.k8s.local
```

2. Setting the account

```bash
gcloud config set account pshandilya@student.ethz.ch
```

3. Setting the project

```bash
gcloud config set project cca-eth-2025-group-20
```
