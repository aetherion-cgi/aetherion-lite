# CEOA Deployment Guide
## From Zero to Production in 4-6 Months

**Version:** 1.0  
**Last Updated:** November 2025  
**Team Size:** 6-9 engineers  
**Estimated LOC:** 40,000-50,000

---

## Table of Contents

1. [Quick Start (Local Development)](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Development Workflow](#development-workflow)
4. [Testing Strategy](#testing-strategy)
5. [Production Deployment](#production-deployment)
6. [Operations & Monitoring](#operations--monitoring)
7. [Scaling Strategy](#scaling-strategy)
8. [Security & Compliance](#security--compliance)

---

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for TypeScript SDK)
- kubectl (for Kubernetes deployment)

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/aetherion/ceoa.git
cd ceoa

# Install Python dependencies
poetry install

# Generate OpenAPI clients (auto-generates SDKs)
./scripts/generate-clients.sh
```

### 2. Start Local Environment

```bash
# Start all services with Docker Compose
docker-compose up -d

# Services available at:
# - CEOA API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Metrics: http://localhost:8000/metrics
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
# - OPA: http://localhost:8181
```

### 3. Run First Workload

```bash
# Submit test workload
curl -X POST http://localhost:8000/ceoa/v1/workloads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test_token" \
  -d '{
    "description": "Test workload",
    "docker_image": "ubuntu:latest",
    "requirements": {
      "cpu_cores": 2,
      "memory_gb": 4,
      "estimated_duration_minutes": 10
    },
    "preferences": {
      "carbon_aware": true,
      "cost_optimize": true
    }
  }'

# Check status
curl http://localhost:8000/ceoa/v1/workloads/{workload_id}
```

---

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                     CEOA Platform                           │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   FastAPI   │  │  Scheduler   │  │  Carbon Engine  │   │
│  │     API     │──│     Core     │──│    (Cache +     │   │
│  └─────────────┘  └──────────────┘  │   Forecasting)  │   │
│         │                            └─────────────────┘   │
│         │                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  PostgreSQL │  │     Redis    │  │       OPA       │   │
│  │  (Topology) │  │   (Cache)    │  │  (Governance)   │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Cloud Provider Adapters                      │  │
│  │   AWS Batch  │  GCP Batch  │  Azure Batch           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────────────┐              ┌─────────────────┐
│  Cloud Infra  │              │  Device Mesh    │
│  (AWS/GCP)    │              │  (Phones/PCs)   │
└───────────────┘              └─────────────────┘
```

### Design Principles (The Compression Playbook)

1. **Contracts → Codegen:** OpenAPI is single source of truth
2. **Policy as Config:** OPA policies in YAML, not Python
3. **Buy Controllers:** Use AWS/GCP Batch, not custom orchestrators
4. **Config-Driven Scheduler:** Weights in YAML, not hardcoded
5. **Cache First:** Simple EMA forecasting, upgrade to ML later
6. **Shared Observability:** One monitoring lib, reused everywhere
7. **KMP for Mobile:** 70% code sharing across Android/iOS

---

## Development Workflow

### Code Generation Pipeline

```bash
# 1. Update OpenAPI spec
vim contracts/openapi.yaml

# 2. Generate clients (Python, TypeScript, Swift, Kotlin)
openapi-generator-cli generate \
  -i contracts/openapi.yaml \
  -g python \
  -o backend/api/generated

openapi-generator-cli generate \
  -i contracts/openapi.yaml \
  -g typescript-fetch \
  -o device-mesh/desktop/generated

# 3. Clients are now in sync with API!
```

### Configuration Hot-Reload

```bash
# Update scheduler weights
vim configs/scheduler.yaml

# Reload without restarting
curl -X POST http://localhost:8000/ceoa/v1/admin/reload-config

# Changes take effect immediately!
```

### Policy Updates (OPA)

```bash
# Update governance policies
vim policies/governance.rego

# Test policy locally
opa test policies/ -v

# Deploy to production (via bundle server)
aws s3 cp policies/ s3://ceoa-opa-bundles/production_v1/ --recursive

# OPA auto-reloads from S3 every 60 seconds
```

---

## Testing Strategy

### Test Pyramid

```
     ┌────────────────┐
     │  E2E Tests     │  ~300 tests
     │  (10%)         │
     ├────────────────┤
     │  Integration   │  ~600 tests
     │  Tests (30%)   │
     ├────────────────┤
     │  Unit Tests    │  ~1,100 tests
     │  (60%)         │
     └────────────────┘

Total: ~2,000 tests (vs. 10,000+ bloated approach)
```

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires Docker)
pytest tests/integration -v

# Contract tests (verify cloud adapters)
pytest tests/contracts -v

# Golden tests (scheduler determinism)
pytest tests/golden -v

# E2E test (full workflow)
pytest tests/e2e -v

# All tests with coverage
pytest --cov=backend --cov-report=html
```

### Golden Tests (Scheduler)

```python
# tests/golden/test_scheduler_determinism.py
def test_placement_is_deterministic():
    """Verify scheduler produces same results for same input"""
    workload = load_golden_workload("test_case_1.json")
    nodes = load_golden_nodes("test_nodes.json")
    carbon = load_golden_carbon("test_carbon.json")
    
    # Run scheduler 10 times
    results = [
        greedy_select_placement(workload, nodes, carbon, CONFIG)
        for _ in range(10)
    ]
    
    # All results should be identical
    assert all(r[0]["node"]["id"] == results[0][0]["node"]["id"] for r in results)
```

---

## Production Deployment

### Infrastructure Setup (AWS Example)

```bash
# 1. Provision infrastructure with Terraform
cd infra/terraform
terraform init
terraform plan
terraform apply

# Resources created:
# - EKS cluster (Kubernetes)
# - RDS PostgreSQL (database)
# - ElastiCache Redis (cache)
# - S3 buckets (OPA bundles, artifacts)
# - IAM roles & policies
```

### Kubernetes Deployment

```bash
# 2. Deploy to Kubernetes with Helm
cd infra/helm

# Install cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Deploy CEOA
helm install ceoa ./ceoa-chart \
  --namespace ceoa \
  --create-namespace \
  --values values.production.yaml

# Verify deployment
kubectl get pods -n ceoa
kubectl logs -n ceoa deployment/ceoa-api -f
```

### Helm Chart Structure

```
infra/helm/ceoa-chart/
├── Chart.yaml
├── values.yaml                 # Default values
├── values.production.yaml      # Production overrides
├── templates/
│   ├── deployment.yaml         # API deployment
│   ├── service.yaml            # LoadBalancer service
│   ├── configmap.yaml          # Scheduler config
│   ├── secret.yaml             # API keys (sealed)
│   ├── ingress.yaml            # HTTPS ingress
│   ├── hpa.yaml                # Horizontal pod autoscaler
│   └── servicemonitor.yaml     # Prometheus monitoring
└── README.md
```

### Environment Configuration

```yaml
# values.production.yaml
replicaCount: 3

image:
  repository: ghcr.io/aetherion/ceoa
  tag: "1.0.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

postgresql:
  host: ceoa-prod.cluster-xxxxx.us-west-2.rds.amazonaws.com
  database: ceoa
  # username/password in sealed secret

redis:
  host: ceoa-prod.xxxxx.cache.amazonaws.com
  port: 6379

carbonApi:
  electricityMaps:
    # API key in sealed secret

scheduler:
  strategy: hybrid  # greedy + batch optimizer
  batchOptimizer:
    enabled: true
    interval_seconds: 60

monitoring:
  prometheus:
    enabled: true
    scrapeInterval: 30s
  
  grafana:
    dashboardsConfigMap: ceoa-dashboards
```

---

## Operations & Monitoring

### Observability Stack

**Metrics:** Prometheus + Grafana
- API latency (p50, p95, p99)
- Workload throughput
- Placement decision latency
- Cost/carbon savings
- Device mesh participation

**Traces:** OpenTelemetry + Jaeger/Tempo
- Distributed request tracing
- End-to-end latency breakdown
- Bottleneck identification

**Logs:** Structured JSON logs → Loki/CloudWatch
- Request/response logging
- Error tracking
- Audit trail

### Key Metrics

```prometheus
# SLI: API Availability
(
  sum(rate(ceoa_http_requests_total{status!~"5.."}[5m]))
  /
  sum(rate(ceoa_http_requests_total[5m]))
) > 0.995  # 99.5% uptime

# SLI: API Latency
histogram_quantile(0.95, ceoa_http_request_duration_seconds) < 1.0  # p95 < 1s

# SLI: Placement Success Rate
(
  sum(rate(ceoa_workloads_completed_total{status="completed"}[5m]))
  /
  sum(rate(ceoa_workloads_completed_total[5m]))
) > 0.98  # 98% success rate

# Carbon Savings
sum(ceoa_workload_carbon_kg) - sum(ceoa_baseline_carbon_kg)  # kg CO2 saved
```

### Alerts (PagerDuty/OpsGenie)

```yaml
# alerting-rules.yaml
groups:
  - name: ceoa_critical
    interval: 1m
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(ceoa_http_requests_total{status="500"}[5m]))
          /
          sum(rate(ceoa_http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected (>5%)"
      
      - alert: PlacementFailures
        expr: |
          rate(ceoa_placement_failures_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High placement failure rate"
      
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL database is down"
```

### Dashboards (Grafana)

1. **Operations Dashboard**
   - Request rate, error rate, latency
   - Active workloads by status
   - Placement decisions per second
   - Database/Redis health

2. **Business Dashboard**
   - Total workloads processed (daily/weekly/monthly)
   - Cost savings ($ and %)
   - Carbon savings (kg CO2)
   - Device mesh participation
   - Revenue (estimated)

3. **Carbon Intelligence Dashboard**
   - Carbon intensity by region
   - Green window coverage
   - Carbon-aware routing effectiveness
   - Energy consumption trends

---

## Scaling Strategy

### Horizontal Scaling

**API Layer:** Stateless, auto-scales based on CPU
```bash
# Kubernetes HPA
kubectl autoscale deployment ceoa-api \
  --min=3 --max=20 \
  --cpu-percent=70
```

**Database:** PostgreSQL with read replicas
```bash
# Primary (writes) + 2 replicas (reads)
# Connection pooling via PgBouncer
```

**Redis:** Redis Cluster for horizontal scaling
```bash
# 3 master nodes + 3 replica nodes
# Automatic sharding
```

### Vertical Scaling

**Batch Optimizer:** Increase resources for OR-Tools
```yaml
resources:
  requests:
    cpu: 2000m
    memory: 8Gi
```

### Geographic Distribution

**Multi-Region Deployment:**
- US-West (primary)
- US-East (secondary)
- EU-West (GDPR compliance)
- APAC (low latency)

**Traffic Routing:**
- Route 53 latency-based routing
- Regional failover
- Global Accelerator for edge acceleration

---

## Security & Compliance

### Authentication & Authorization

**API Authentication:**
- JWT tokens (short-lived)
- API keys for services
- mTLS for service-to-service

**OPA Policies:**
- Data residency enforcement
- Export control compliance
- Benefit/harm scoring
- Cost limits per tier

### Data Protection

**Encryption:**
- At rest: AES-256 (RDS, S3)
- In transit: TLS 1.3
- E2E encryption for device mesh

**Secrets Management:**
- Sealed Secrets (Kubernetes)
- AWS Secrets Manager
- Automatic rotation

### Compliance Certifications

**Target Certifications:**
- SOC 2 Type II (6-12 months)
- ISO 27001 (12-18 months)
- GDPR compliance (immediate)
- HIPAA (if healthcare workloads)

### Audit Trail

**Immutable Logs:**
- All governance decisions logged
- Workload placement history
- Cost/carbon calculations
- Policy evaluations

**Retention:**
- 90 days hot (Loki/CloudWatch)
- 7 years cold (S3 Glacier)

---

## Deployment Checklist

### Pre-Production
- [ ] Load testing (1000+ req/s sustained)
- [ ] Chaos engineering (kill pods randomly)
- [ ] Disaster recovery tested
- [ ] Backup & restore verified
- [ ] Security audit completed
- [ ] Documentation complete
- [ ] Runbooks written

### Production Launch
- [ ] Blue-green deployment configured
- [ ] Monitoring dashboards live
- [ ] Alerts configured and tested
- [ ] On-call rotation established
- [ ] Incident response plan ready
- [ ] Customer communication plan
- [ ] Rollback plan tested

### Post-Launch
- [ ] Monitor error rates
- [ ] Track SLIs/SLOs
- [ ] Gather customer feedback
- [ ] Optimize placement algorithm
- [ ] Update weights based on data
- [ ] Plan v2 features

---

## Timeline & Milestones

### Month 1-2: Foundation
- ✅ Core API operational
- ✅ PostgreSQL topology working
- ✅ AWS Batch adapter complete
- ✅ Scheduler (greedy) deployed
- ✅ Carbon cache operational

### Month 3-4: Intelligence
- ✅ GCP Batch adapter
- ✅ Batch optimizer (OR-Tools)
- ✅ Carbon forecasting (EMA)
- ✅ OPA policies deployed
- ✅ Device mesh SDK (MVP)

### Month 5-6: Production
- ✅ Multi-region deployment
- ✅ SOC 2 audit started
- ✅ 10 pilot customers
- ✅ Device mesh (1,000 devices)
- ✅ $100k+ ARR

---

## Support & Resources

**Documentation:** https://docs.aetherion.ai/ceoa  
**API Reference:** https://api.aetherion.ai/ceoa/docs  
**Status Page:** https://status.aetherion.ai  
**Support:** support@aetherion.ai  
**Slack:** #ceoa-platform

---

**Built with the compression playbook. Deployed with confidence. Scaled with humanity.**
