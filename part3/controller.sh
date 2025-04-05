#!/bin/bash

# Start all the static workloads
echo "Starting memcached, blackscholes, and canneal..."
kubectl apply -f memcache-t1-cpuset.yaml
kubectl apply -f part3/parsec-blackscholes.yaml
kubectl apply -f part3/parsec-canneal.yaml

echo "Starting sequential execution on node-c-4core..."
# Launch freqmine on node-c
kubectl apply -f part3/parsec-freqmine.yaml
echo "Waiting for freqmine to complete before starting radix..."
kubectl wait --for=condition=complete job/parsec-freqmine --timeout=3h
# Launch radix after freqmine completes
kubectl apply -f part3/parsec-radix.yaml

echo "Starting sequential execution on node-d-4core..."
# Launch ferret on node-d
kubectl apply -f part3/parsec-ferret.yaml
echo "Waiting for ferret to complete before starting vips..."
kubectl wait --for=condition=complete job/parsec-ferret --timeout=3h
# Launch vips after ferret completes
kubectl apply -f part3/parsec-vips.yaml
echo "Waiting for vips to complete before starting dedup..."
kubectl wait --for=condition=complete job/parsec-vips --timeout=3h
# Launch dedup after vips completes
kubectl apply -f part3/parsec-dedup.yaml

echo "All jobs launched. Monitor status with: kubectl get pods,jobs"
