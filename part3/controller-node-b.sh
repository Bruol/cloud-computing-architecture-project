#!/bin/bash

echo "Starting controller for node-b-2core (blackscholes)..."

# Function to run blackscholes with restart handling
run_blackscholes() {
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Starting blackscholes (attempt $attempt)..."
    kubectl apply -f part3/parsec-blackscholes.yaml

    # Check if job completes successfully
    if kubectl wait --for=condition=complete job/parsec-blackscholes --timeout=2h; then
      echo "Blackscholes completed successfully."
      return 0
    else
      echo "Blackscholes failed on attempt $attempt."
      kubectl delete job parsec-blackscholes --ignore-not-found
      attempt=$((attempt + 1))
      sleep 10
    fi
  done

  echo "Failed to run blackscholes after $max_attempts attempts."
  return 1
}

# Run blackscholes with restart handling
run_blackscholes
