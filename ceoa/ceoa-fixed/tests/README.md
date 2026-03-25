# Tests Directory

This directory is structured and ready for test implementation.

## Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for service interactions
└── golden/         # Golden tests for deterministic behavior
```

## Test Strategy

### Unit Tests (~7k LOC to add)
- `test_scheduler_core.py` - Scheduler placement logic
- `test_cloud_adapters.py` - AWS/GCP adapter behavior
- `test_carbon_engine.py` - Carbon intelligence caching
- `test_models.py` - Database model validation
- `test_governance.py` - OPA policy integration

### Integration Tests (~3k LOC to add)
- `test_api_endpoints.py` - FastAPI endpoint integration
- `test_database.py` - PostgreSQL integration
- `test_redis.py` - Redis caching integration
- `test_opa.py` - OPA policy server integration

### Golden Tests (~500 LOC to add)
- `test_scheduler_determinism.py` - Verify placement is deterministic
- `test_cost_calculations.py` - Verify cost estimation accuracy
- `test_carbon_forecasts.py` - Verify forecast consistency

## Running Tests

```bash
# Install test dependencies
poetry install --with dev

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/golden/ -v
```

## Test Coverage Target

- **Unit Tests:** 80%+ coverage
- **Integration Tests:** Key workflows covered
- **Golden Tests:** Critical algorithms verified

---

**Status:** Framework ready, tests to be implemented
