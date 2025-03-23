1. Since I have different gcloud account, so fixing the context issue

```bash
# Create or switch to your intended context
kubectl config set-context part1.k8s.local --cluster=part1.k8s.local

# Use this context
kubectl config use-context part1.k8s.local
```