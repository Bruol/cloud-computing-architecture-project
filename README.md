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

This will generate the logs in the `part1/logs` folder.
