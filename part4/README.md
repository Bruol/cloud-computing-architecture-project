# Set Up the Environment

## Install Ansible

```bash
sudo apt-get install ansible
```

## Start the VMs

```bash
export KOPS_STATE_STORE=<your-gcp-state-store>
PROJECT='gcloud config get-value project'
kops create -f part4.yaml
```

```bash
kops update cluster --name part4.k8s.local --yes --admin
kops validate cluster --wait 10m
```

get the IPs

```bash
kubectl get nodes -o wide
```

## Modify the Inventory File

1. Open the `ansible/inventory.yaml` file and modify the IPs to the public IPs of the nodes
2. Replace the `mcperf_command` with the command you want to run

## Run the Playbook

```bash
ansible-playbook -i inventory.yml playbook.yml
```

## start the load

```bash
ssh ubuntu@<client-measure-ip>
cd memcache-perf-dynamic
./run_load.sh
```

## destroy the VMs

```bash
kops delete cluster --name part4.k8s.local --yes
```
