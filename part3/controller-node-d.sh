#!/bin/bash

echo "Starting controller for node-d-4core (ferret, vips, dedup)..."

# Function to run a job with restart handling
run_job() {
  local job_name=$1
  local yaml_file=$2
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Starting $job_name (attempt $attempt)..."
    kubectl apply -f $yaml_file

    # Check if job completes successfully
    if kubectl wait --for=condition=complete job/$job_name --timeout=2h; then
      echo "$job_name completed successfully."
      return 0
    else
      echo "$job_name failed on attempt $attempt."
      kubectl delete job $job_name --ignore-not-found
      attempt=$((attempt + 1))
      sleep 10
    fi
  done

  echo "Failed to run $job_name after $max_attempts attempts."
  return 1
}

# Run jobs sequentially with restart handling
run_job parsec-ferret part3/parsec-ferret.yaml
run_job parsec-vips part3/parsec-vips.yaml
run_job parsec-dedup part3/parsec-dedup.yaml
