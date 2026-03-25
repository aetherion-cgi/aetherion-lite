# UIE - QUICK START GUIDE

## Instant Deployment (5 Minutes)

```bash
# 1. Navigate to project
cd universal-intelligence-engine

# 2. Start all services
docker-compose up -d

# 3. Check health
curl http://localhost:8000/health

# 4. Send first request
curl -X POST http://localhost:8000/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo",
    "actor": "user1",
    "intent": {"task": "query", "domains": ["general"]},
    "payload": {"text": "What is AI?"},
    "policy": {"region": "US"}
  }'
```

## Services URLs
- **UIE API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)
- **OPA:** http://localhost:8181

## Key Files
- **Main API:** `uie/api/gateway.py`
- **Schemas:** `uie/core/schemas.py`
- **Orchestrator:** `uie/core/orchestrator.py`
- **Catalogs:** `config/tools/`, `config/prompts/`, `config/models/`
- **Policies:** `config/opa/ingress.rego`, `config/opa/egress.rego`

## Common Commands
```bash
make help           # Show all commands
make docker-up      # Start services
make docker-down    # Stop services
make logs           # View UIE logs
make test           # Run tests
make health         # Check health
```

## Next Steps
1. Review `BUILD_SUMMARY.md` for complete overview
2. Read `README.md` for detailed documentation
3. Examine catalogs in `config/` directory
4. Run tests with `make test`
5. Integrate with Cortex Gateway

## Project Structure
```
universal-intelligence-engine/
├── uie/                    # Core application
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Core components
│   ├── adapters/          # LLM adapters
│   ├── catalogs/          # Catalog loaders
│   ├── security/          # OPA integration
│   └── observability/     # Tracing & metrics
├── config/                # Configuration
│   ├── tools/            # Tool catalog
│   ├── prompts/          # Prompt templates
│   ├── models/           # Model capabilities
│   └── opa/              # Security policies
├── tests/                # Test suite
├── deployment/           # Deployment configs
├── docker-compose.yml    # Service orchestration
├── Dockerfile           # Container build
└── README.md            # Full documentation
```

## Support
- **Build Summary:** `BUILD_SUMMARY.md`
- **Full Docs:** `README.md`
- **Tests:** `tests/unit/test_intent_understanding.py`

**Status:** ✅ READY FOR DEPLOYMENT

