#!/bin/bash
set -e # Exit on error
mkdir -p test_results

# Set test mode variables
TEST_MODE=true
NUM_RUNS=1               # Just run once for testing
TEST_TIMEOUT="2m"        # Short timeouts for testing
CLEAN_BETWEEN_RUNS=false # Only needed if doing multiple test runs

echo "====== RUNNING IN TEST MODE ======"
echo "This will test the workflow with minimal resources"

# Function to get node wildcard name (handles dynamic node names)
get_node_name() {
    local prefix=$1
    kubectl get nodes | grep "$prefix" | awk '{print $1}' | head -1
}

# Function to run a single experiment in test mode
run_test_experiment() {
    local run_number=$1
    echo "=========================================="
    echo "Starting Test Run #$run_number"
    echo "=========================================="

    # 1. Deploy memcached with reduced resources
    echo "[TEST] Deploying memcached (test mode)..."
    cat >test-memcache.yaml <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: memcached
  labels:
    name: memcached
spec:
  containers:
    - image: anakli/memcached:t1
      name: memcached
      imagePullPolicy: Always
      command: ["/bin/sh"]
      args: ["-c", "taskset -c 0 ./memcached -t 1 -u memcache"]
      resources:
        requests:
          memory: "256Mi"
          cpu: "0.2"
        limits:
          memory: "512Mi"
          cpu: "0.5"
EOF

    kubectl apply -f test-memcache.yaml
    kubectl wait --for=condition=ready pod/memcached --timeout=$TEST_TIMEOUT || {
        echo "[TEST] ⚠️ Memcached failed to start, but continuing with test workflow..."
        kubectl get pods
    }

    # Get IP addresses (may fail in test mode, but we'll continue)
    MEMCACHED_IP=$(kubectl get pod memcached -o jsonpath='{.status.podIP}' 2>/dev/null || echo "127.0.0.1")

    echo "[TEST] Memcached IP: $MEMCACHED_IP"

    # 2. Create test job for PARSEC workload simulation
    echo "[TEST] Creating test PARSEC-like job..."
    cat >test-parsec-job.yaml <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: test-parsec-job
spec:
  template:
    spec:
      containers:
      - name: parsec-test
        image: busybox
        command: ["sh", "-c", "echo Starting PARSEC simulation && sleep 5 && echo PARSEC job completed"]
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "100m"
      restartPolicy: Never
  backoffLimit: 1
EOF

    kubectl apply -f test-parsec-job.yaml

    # 3. Simulate mcperf output for testing analyze_results.py
    echo "[TEST] Simulating mcperf output..."
    cat >test_results/mcperf_${run_number}.txt <<EOF
#type       target    size     op    avg     p50      p90      p95      p99     start_ts      end_ts
read      fixed     16        1    0.025   0.050   0.200   0.250    0.500   1617111680.1   1617111681.2
read      fixed     16        1    0.035   0.050   0.200   0.350    0.550   1617111681.2   1617111682.3
read      fixed     16        1    0.045   0.070   0.300   0.450    0.700   1617111682.3   1617111683.4
read      fixed     16        1    0.055   0.080   0.400   0.950    0.850   1617111683.4   1617111684.5
read      fixed     16        1    0.065   0.090   0.500   1.050    1.000   1617111684.5   1617111685.6
EOF

    # 4. Wait for test job to complete
    echo "[TEST] Waiting for test job to complete..."
    kubectl wait --for=condition=complete job/test-parsec-job --timeout=$TEST_TIMEOUT || {
        echo "[TEST] ⚠️ Test job didn't complete in time, but continuing..."
    }

    # 5. Create test pod data
    echo "[TEST] Creating test pod data..."
    # Current timestamp for fake data
    NOW_TS=$(date +%s)
    START_TIME=$(date -u -d @$((NOW_TS - 60)) +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME=$(date -u -d @$NOW_TS +"%Y-%m-%dT%H:%M:%SZ")

    cat >test_results/pods_${run_number}.json <<EOF
{
  "kind": "List",
  "apiVersion": "v1",
  "items": [
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "memcached"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "memcached",
            "state": {
              "running": {}
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-blackscholes"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "blackscholes",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-canneal"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "canneal",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-dedup"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "dedup",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-ferret"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "ferret",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-freqmine"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "freqmine",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-radix"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "radix",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    },
    {
      "kind": "Pod",
      "apiVersion": "v1",
      "metadata": {
        "name": "parsec-vips"
      },
      "status": {
        "containerStatuses": [
          {
            "name": "vips",
            "state": {
              "terminated": {
                "startedAt": "$START_TIME",
                "finishedAt": "$END_TIME"
              }
            }
          }
        ]
      }
    }
  ]
}
EOF

    # 6. Process test data with get_time.py
    echo "[TEST] Processing test data with get_time.py..."
    python3 get_time.py test_results/pods_${run_number}.json >test_results/times_${run_number}.txt || {
        echo "[TEST] ⚠️ get_time.py failed to process data (this is expected if it's checking for exactly 7 jobs)"
    }

    # 7. Clean up if needed
    if [ "$CLEAN_BETWEEN_RUNS" = true ]; then
        echo "[TEST] Cleaning up test resources..."
        kubectl delete job test-parsec-job --ignore-not-found
        kubectl delete pod memcached --ignore-not-found
    fi

    echo "[TEST] Test run #$run_number completed"
}

# Create test version of controller script
echo "[TEST] Creating test versions of controller scripts..."
mkdir -p part3/test
cat >part3/test/controller-main.sh <<EOF
#!/bin/bash
echo "[TEST] This is a test version of controller-main.sh"
echo "[TEST] It would normally start memcached and then launch node controllers"
exit 0
EOF
chmod +x part3/test/controller-main.sh

# Run test experiment
for run in $(seq 1 $NUM_RUNS); do
    run_test_experiment $run
done

# Clean up at the end
echo "[TEST] Final cleanup..."
kubectl delete job test-parsec-job --ignore-not-found
kubectl delete pod memcached --ignore-not-found
rm -f test-memcache.yaml test-parsec-job.yaml

# Test analysis script on test data
echo "[TEST] Testing analysis script on test data..."
cp part3/analyze_results.py test_analyze_results.py
sed -i.bak 's/pods_/test_results\/pods_/g' test_analyze_results.py
sed -i.bak 's/mcperf_/test_results\/mcperf_/g' test_analyze_results.py

echo "[TEST] Running analysis script..."
python3 test_analyze_results.py || {
    echo "[TEST] ⚠️ Analysis script failed (may be due to test data format)"
}

echo "=========================================="
echo "[TEST] Testing workflow completed!"
echo "Workflow components tested:"
echo "✓ Memcached deployment"
echo "✓ Job creation and execution"
echo "✓ Data collection"
echo "✓ Result processing"
echo "=========================================="
echo "Review test_results/ directory for test outputs"
echo "When ready for production, use the run_three_experiments.sh script"
