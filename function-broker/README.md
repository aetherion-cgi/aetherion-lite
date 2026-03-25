# Aetherion Function Broker

The Function Broker is the internal service that maps `capability_id + Envelope → NormalizedResult` by communicating with Aetherion's internal engines.

## Architecture

The Function Broker sits between the Cortex Gateway and the internal engines, providing:

```
Cortex Gateway → Function Broker → [Adapters] → Internal Engines
                                        ↓
                                   [BUE, URPE, UDOA, CEOA, UIE, ILE, Domain Cortex]
```

## Key Responsibilities

1. **Capability Registry**: Maintains a catalog of all available capabilities
2. **Adapter Management**: Routes requests to appropriate engine adapters
3. **Security Enforcement**: Validates authentication, authorization, and governance constraints
4. **Response Sanitization**: Ensures no internal details are exposed
5. **Metrics Collection**: Tracks invocation metrics for observability

## Project Structure

```
function-broker/
├── broker/
│   ├── api/
│   │   └── main.py              # FastAPI application
│   ├── core/
│   │   ├── models.py            # Capability descriptors
│   │   ├── registry.py          # Capability registry
│   │   ├── security.py          # Security enforcement
│   │   └── broker_service.py    # Core orchestration logic
│   ├── adapters/
│   │   ├── base.py              # Abstract adapter class
│   │   ├── uie_adapter.py       # UIE adapter
│   │   ├── bue_adapter.py       # BUE adapter
│   │   ├── udoa_adapter.py      # UDOA adapter
│   │   ├── ceoa_adapter.py      # CEOA adapter
│   │   ├── urpe_adapter.py      # URPE adapter (CRITICAL)
│   │   ├── ile_adapter.py       # ILE adapter
│   │   └── domain_cortex_adapter.py  # Domain Cortex adapter
│   ├── config/
│   │   ├── capabilities.yaml    # Capability definitions
│   │   └── settings.py          # Configuration
│   └── observability/
│       ├── logging.py           # Structured logging
│       └── metrics.py           # Metrics collection
├── tests/
├── Dockerfile
└── pyproject.toml
```

## Capabilities

Capabilities are defined in `config/capabilities.yaml`. Each capability specifies:

- **id**: Unique identifier (e.g., `bue.underwrite`)
- **adapter**: Adapter class to use
- **endpoint**: Engine HTTP endpoint
- **governance_tier**: Default authorization tier
- **domains**: Domain classifications
- **timeout**: Request timeout in seconds

### Available Capabilities

| Capability ID | Engine | Purpose |
|--------------|--------|---------|
| `uie.query` | UIE | General reasoning and synthesis |
| `bue.underwrite` | BUE | Business underwriting analysis |
| `udoa.query` | UDOA | Governed data access |
| `ceoa.schedule` | CEOA | Compute workload scheduling |
| `urpe.evaluate` | URPE | Strategic/existential risk evaluation |
| `ile.learn` | ILE | Constitutional learning |
| `cortex.synthesize` | Domain Cortex | Cross-domain synthesis |

## API Endpoints

### POST /v1/invoke

Invoke a capability with an envelope.

**Request:**
```json
{
  "capability_id": "bue.underwrite",
  "envelope": {
    "tenant_id": "acme-corp",
    "actor": "user@example.com",
    "intent": {
      "task": "underwriting",
      "domains": ["finance"]
    },
    "payload": {
      "scenario": "commercial_loan"
    },
    "governance": {
      "requested_tier": "T2",
      "region": "US"
    }
  }
}
```

**Response:**
```json
{
  "data": {...},
  "details": {...},
  "governance": {...},
  "traces": {
    "capability_id": "bue.underwrite",
    "bue_request_id": "..."
  },
  "success": true
}
```

### GET /v1/capabilities

List available capabilities for a tenant.

### GET /health

Health check endpoint.

### GET /metrics

Prometheus metrics endpoint.

## Security

### Internal-Only Access

The Function Broker is **NEVER** exposed to the public internet. It is only accessible via:

- Service mesh internal networking
- mTLS authentication
- Internal service identities

### Governance Enforcement

All invocations are subject to constitutional governance:

1. **Tier Validation**: Ensures requested tier meets capability requirements
2. **Tenant Isolation**: Enforces multi-tenancy boundaries
3. **Actor Authorization**: Validates actor permissions
4. **PII Protection**: Masks sensitive data when required

### URPE Special Handling

URPE (Universal Risk & Probabilistic Engine) has special security rules:

- **ONLY** accessible via `urpe.evaluate` capability
- Requires T3 governance tier (critical review)
- All calls are audited
- Additional validation in URPEAdapter
- Never directly exposed

## Adapters

### Base Adapter Pattern

All adapters inherit from `BaseAdapter` and implement:

```python
async def call(self, envelope: Envelope) -> NormalizedResult:
    # 1. Build engine-specific request
    # 2. Call engine via HTTP/Kafka
    # 3. Sanitize response
    # 4. Return NormalizedResult
```

### Adapter Responsibilities

1. **Translation**: Convert Envelope to engine format
2. **Communication**: Handle HTTP/Kafka calls with retry logic
3. **Sanitization**: Remove internal details from responses
4. **Error Handling**: Return clean error messages

### Adding New Adapters

To add a new engine:

1. Create adapter class in `broker/adapters/`
2. Add capability entry in `config/capabilities.yaml`
3. No other changes needed!

## Configuration

### Environment Variables

```bash
# Service configuration
BROKER_HOST=0.0.0.0
BROKER_PORT=8100
BROKER_LOG_LEVEL=INFO
BROKER_ENVIRONMENT=production

# Security
BROKER_STRICT_SECURITY=true
BROKER_REQUIRE_MTLS=true

# Certificates
BROKER_CA_BUNDLE=/etc/ssl/certs/aetherion-ca.crt
BROKER_SERVER_CERT=/etc/ssl/certs/function-broker.crt
BROKER_SERVER_KEY=/etc/ssl/private/function-broker.key

# Timeouts
BROKER_DEFAULT_TIMEOUT=30
BROKER_URPE_TIMEOUT=120
BROKER_BUE_TIMEOUT=60
```

## Development

### Setup

```bash
# Install dependencies
pip install -e .
pip install -e ../aetherion-common

# Run tests
pytest

# Run locally
uvicorn broker.api.main:app --reload --port 8100
```

### Adding a New Capability

1. Add entry to `capabilities.yaml`:
```yaml
- id: "new_engine.operation"
  display_name: "New Engine Operation"
  adapter: "NewEngineAdapter"
  adapter_type: "http"
  endpoint: "http://new-engine:8000/api/v1/operation"
  default_governance_tier: "T2"
  domains: ["new_domain"]
```

2. Create adapter in `broker/adapters/new_engine_adapter.py`:
```python
from .base import BaseAdapter

class NewEngineAdapter(BaseAdapter):
    async def call(self, envelope: Envelope) -> NormalizedResult:
        # Implementation
        pass
```

3. Register in `broker/adapters/__init__.py`

That's it! The broker will automatically load and use the new capability.

## Deployment

### Docker

```bash
docker build -t aetherion/function-broker:latest .
docker run -p 8100:8100 aetherion/function-broker:latest
```

### Kubernetes

Deploy as an internal service with:
- Service mesh integration (Istio/Linkerd)
- mTLS certificates mounted
- Internal ClusterIP service (no LoadBalancer)
- Resource limits set appropriately

## Monitoring

### Metrics

The broker exposes Prometheus metrics at `/metrics`:

- `broker_invocations_total`: Total invocations by capability and status
- `broker_duration_seconds`: Invocation duration histogram
- `broker_errors_total`: Errors by type

### Logging

Structured JSON logs include:
- Request ID and trace ID
- Tenant and actor
- Capability invoked
- Success/failure status
- Duration

### Tracing

Distributed traces are sent to Jaeger for end-to-end visibility:
- Span per capability invocation
- Child spans for engine calls
- Governance decision traces

## Lines of Code

Estimated: ~1,500 lines

Actual breakdown:
- Core logic: ~400 LOC
- Adapters: ~600 LOC (7 adapters × ~85 LOC each)
- API: ~200 LOC
- Configuration: ~200 LOC
- Observability: ~100 LOC

## Version

1.0.0
