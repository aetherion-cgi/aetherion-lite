# Infrastructure as Code

This directory contains infrastructure configuration for deploying CEOA to production.

## Structure

```
infra/
├── terraform/      # Terraform modules for AWS/GCP resources
├── helm/           # Kubernetes Helm charts
└── k8s/            # Kubernetes manifests
```

## Terraform (~1.5k LOC to add)

### AWS Resources
- `terraform/aws/rds.tf` - PostgreSQL database
- `terraform/aws/elasticache.tf` - Redis cache
- `terraform/aws/eks.tf` - Kubernetes cluster
- `terraform/aws/s3.tf` - Storage buckets
- `terraform/aws/iam.tf` - IAM roles and policies

### GCP Resources  
- `terraform/gcp/cloudsql.tf` - PostgreSQL database
- `terraform/gcp/memorystore.tf` - Redis cache
- `terraform/gcp/gke.tf` - Kubernetes cluster
- `terraform/gcp/storage.tf` - Cloud Storage buckets
- `terraform/gcp/iam.tf` - Service accounts

## Helm Charts (~1k LOC to add)

### CEOA Chart
- `helm/ceoa/Chart.yaml` - Chart metadata
- `helm/ceoa/values.yaml` - Default configuration
- `helm/ceoa/values.production.yaml` - Production overrides
- `helm/ceoa/templates/deployment.yaml` - API deployment
- `helm/ceoa/templates/service.yaml` - LoadBalancer service
- `helm/ceoa/templates/ingress.yaml` - HTTPS ingress
- `helm/ceoa/templates/configmap.yaml` - Configuration
- `helm/ceoa/templates/hpa.yaml` - Autoscaling

## Kubernetes Manifests (~500 LOC to add)

### Core Services
- `k8s/postgres.yaml` - PostgreSQL StatefulSet
- `k8s/redis.yaml` - Redis Deployment
- `k8s/opa.yaml` - OPA server
- `k8s/prometheus.yaml` - Monitoring
- `k8s/grafana.yaml` - Dashboards

## Deployment

```bash
# Terraform - Provision infrastructure
cd infra/terraform/aws
terraform init
terraform plan
terraform apply

# Helm - Deploy to Kubernetes
helm install ceoa ./infra/helm/ceoa \
  --namespace ceoa \
  --create-namespace \
  --values values.production.yaml

# Verify deployment
kubectl get pods -n ceoa
kubectl logs -n ceoa deployment/ceoa-api -f
```

---

**Status:** Directory structure ready, configurations to be added
