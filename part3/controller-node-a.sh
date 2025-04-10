#!/bin/bash

echo "Starting controller for node-a-2core (canneal)..."

# Function to run canneal with restart handling
run_canneal() {
  local max_attempts=3
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "Starting canneal (attempt $attempt)..."
    kubectl apply -f part3/parsec-canneal.yaml

    # Check if job completes successfully
    if kubectl wait --for=condition=complete job/parsec-canneal --timeout=2h; then
      echo "Canneal completed successfully."
      return 0
    else
      echo "Canneal failed on attempt $attempt."
      kubectl delete job parsec-canneal --ignore-not-found
      attempt=$((attempt + 1))
      sleep 10
    fi
  done

  echo "Failed to run canneal after $max_attempts attempts."
  return 1
}

# Run canneal with restart handling
run_canneal
