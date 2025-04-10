#!/bin/bash
set -e # Exit on error
mkdir -p part_3_results_group_020

# Function to get node wildcard name (handles dynamic node names)
get_node_name() {
    local prefix=$1
    kubectl get nodes | grep "$prefix" | awk '{print $1}' | head -1
}

# Function to run a single experiment
run_experiment() {
    local run_number=$1
    echo "=========================================="
    echo "Starting Run #$run_number"
    echo "=========================================="

    # 1. Deploy memcached
    echo "Starting memcached on node-b-2core..."
    kubectl apply -f memcache-t1-cpuset.yaml
    kubectl wait --for=condition=ready pod/memcached --timeout=5m

    # Get IP addresses
    MEMCACHED_IP=$(kubectl get pod memcached -o jsonpath='{.status.podIP}')

    # Get node names
    CLIENT_AGENT_A=$(get_node_name "client-agent-a")
    CLIENT_AGENT_B=$(get_node_name "client-agent-b")
    CLIENT_MEASURE=$(get_node_name "client-measure")

    # Get agent IPs using node names
    AGENT_A_IP=$(kubectl get node $CLIENT_AGENT_A -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
    AGENT_B_IP=$(kubectl get node $CLIENT_AGENT_B -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')

    echo "Memcached IP: $MEMCACHED_IP"
    echo "Agent A: $CLIENT_AGENT_A ($AGENT_A_IP)"
    echo "Agent B: $CLIENT_AGENT_B ($AGENT_B_IP)"
    echo "Measure node: $CLIENT_MEASURE"

    # 2. Start mcperf load generators on agents (in background)
    echo "Starting mcperf load generators..."

    # Agent A load generator
    gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@$CLIENT_AGENT_A \
        --zone europe-west1-b -- "cd memcache-perf-dynamic && ./mcperf -T 2 -A" &
    AGENT_A_PID=$!

    # Agent B load generator
    gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@$CLIENT_AGENT_B \
        --zone europe-west1-b -- "cd memcache-perf-dynamic && ./mcperf -T 4 -A" &
    AGENT_B_PID=$!

    # Wait for load generators to start
    sleep 10

    # 3. Start mcperf measurement (in foreground to capture output)
    echo "Starting mcperf measurement..."
    gcloud compute ssh --ssh-key-file ~/.ssh/cloud-computing ubuntu@$CLIENT_MEASURE \
        --zone europe-west1-b -- "cd memcache-perf-dynamic && \
        ./mcperf -s $MEMCACHED_IP --loadonly && \
        ./mcperf -s $MEMCACHED_IP -a $AGENT_A_IP -a $AGENT_B_IP \
        --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 \
        --scan 30000:30500:5" >part_3_results_group_020/mcperf_${run_number}.txt &
    MCPERF_PID=$!

    # 4. Start controller scripts to run PARSEC jobs
    echo "Starting PARSEC jobs via controller scripts..."
    ./part3/controller-main.sh

    # 5. Wait for mcperf measurement to complete
    echo "Waiting for measurement to complete..."
    wait $MCPERF_PID || true

    # 6. Collect pod data
    echo "Collecting pod data..."
    kubectl get pods -o json >part_3_results_group_020/pods_${run_number}.json

    # 7. Process execution times (for verification)
    python3 get_time.py part_3_results_group_020/pods_${run_number}.json >part_3_results_group_020/times_${run_number}.txt

    # 8. Clean up
    echo "Cleaning up..."
    # Kill background processes
    kill $AGENT_A_PID $AGENT_B_PID 2>/dev/null || true

    # Delete Kubernetes resources
    kubectl delete jobs --all
    kubectl delete pod memcached

    echo "Run #$run_number completed"
    echo "Waiting 60 seconds before next run..."
    sleep 60
}

# Run all three experiments
for run in 1 2 3; do
    run_experiment $run
done

echo "All experiments completed!"
echo "Results are stored in the part_3_results_group_020 directory."

# Verify all required files exist
echo "Verifying results..."
for run in 1 2 3; do
    if [ ! -f "part_3_results_group_020/pods_${run}.json" ]; then
        echo "Warning: pods_${run}.json is missing"
    fi

    if [ ! -f "part_3_results_group_020/mcperf_${run}.txt" ]; then
        echo "Warning: mcperf_${run}.txt is missing"
    fi
done

echo "You can now analyze the results."
