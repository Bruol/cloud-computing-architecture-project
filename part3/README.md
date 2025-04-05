# Part 3: Co-scheduling Latency-Critical and Batch Applications

This part combines the latency-critical memcached application from Part 1 and the seven batch applications from Part 2 in a heterogeneous cluster environment. Our scheduling policy optimizes resource usage while minimizing interference.

## Cluster Configuration

- 1 VM for the Kubernetes master
- 3 VMs for mcperf clients (2 agents and 1 measure machine)
- 4 heterogeneous worker VMs:
  - node-a-2core: e2-highmem-2 (2 cores, high memory)
  - node-b-2core: n2-highcpu-2 (2 cores, high CPU)
  - node-c-4core: c3-highcpu-4 (4 cores, high CPU)
  - node-d-4core: n2-standard-4 (4 cores, balanced)

## Scheduling Policy

Our scheduling strategy balances workload characteristics with node capabilities:

1. node-a-2core: Runs `canneal` (memory-intensive benchmark)
   - Placed on e2-highmem-2 to leverage higher memory capacity for this memory-intensive workload

2. node-b-2core: Runs `memcached` and `blackscholes` in parallel
   - `memcached` is CPU-pinned to core 0 to ensure consistent latency
   - `blackscholes` is CPU-pinned to core 1 to prevent interference
   - n2-highcpu-2 provides good CPU performance for both applications

3. node-c-4core: Runs `freqmine` and `radix` sequentially
   - c3-highcpu-4 with SSD storage provides optimal compute and I/O performance
   - Sequential execution to avoid resource contention

4. node-d-4core: Runs `ferret`, `vips`, and `dedup` sequentially
   - n2-standard-4 provides balanced compute/memory resources suitable for these varied workloads
   - Sequential execution maximizes resource availability for each application

## Implementation Details

1. Node/pod affinity rules enforce VM-specific placement
2. CPU pinning using `taskset` isolates workloads on specific cores
3. A controller script orchestrates the sequential execution of batch applications
4. Resource requests/limits enforce proper resource allocation for each application
