# Aetherion AI Agents - Deployment Guide

## Quick Start (5 Minutes)

### 1. Setup Environment

```bash
# Clone/copy the aetherion_agents directory to your project
cd your-aetherion-project

# Install dependencies
pip install -r aetherion_agents/requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export DATABASE_URL="postgresql://user:pass@localhost:5432/aetherion"
```

### 2. Run Integration Example

```bash
# Run the complete integration example
python aetherion_agents/examples/complete_integration.py
```

This will demonstrate all four agents working together on an M&A analysis scenario.

### 3. Integrate with Existing Aetherion Platform

```python
# In your existing Aetherion code
from aetherion_agents import CEOAAgent, UIEAgent, UDOAAgent, ILEAgent

# Initialize agents
ceoa = CEOAAgent()
uie = UIEAgent()
udoa = UDOAAgent()
ile = ILEAgent()

# Use agents in your platform
result = await uie.synthesize(
    query="Your query here",
    persona="analyst"
)
```

## Architecture Integration

### Integration with Existing Engines

The four agents integrate seamlessly with Aetherion's existing engines:

```
┌─────────────────────────────────────────────────────────────┐
│             Aetherion Cortex Gateway (Entry Point)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Function Broker                           │
│              (Routes requests to engines/agents)             │
└─────────────────────────────────────────────────────────────┘
                              ↓
    ┌─────────────┬──────────────┬──────────────┬─────────────┐
    │             │              │              │             │
┌───────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│  BUE  │    │  URPE  │    │  UDOA  │    │  CEOA  │    │   UIE  │
│(Exists)│    │(Exists)│    │ AGENT  │    │ AGENT  │    │ AGENT  │
│ 85%   │    │  95%   │    │  NEW   │    │  NEW   │    │  NEW   │
└───────┘    └────────┘    └────────┘    └────────┘    └────────┘
                              │              │              │
                              └──────────────┴──────────────┘
                                            ↓
                                      ┌────────┐
                                      │  ILE   │
                                      │ AGENT  │
                                      │  NEW   │
                                      └────────┘
                                            ↓
                              ┌────────────────────────┐
                              │ Constitutional         │
                              │ Governance (Validates) │
                              └────────────────────────┘
```

### Key Integration Points

**1. Cortex Gateway Integration**

Add agent routing to your existing Cortex Gateway:

```python
# In cortex_gateway/main.py

from aetherion_agents import CEOAAgent, UIEAgent, UDOAAgent

# Initialize agents
ceoa_agent = CEOAAgent()
uie_agent = UIEAgent()
udoa_agent = UDOAAgent()

@app.post("/query")
async def handle_query(request: QueryRequest):
    # UIE orchestrates the response
    result = await uie_agent.synthesize(
        query=request.query,
        persona=request.user_persona
    )
    
    return result
```

**2. Function Broker Integration**

Add agent endpoints to Function Broker routing:

```python
# In function_broker/router.py

ENGINE_ROUTES = {
    "bue": "http://localhost:8003/bue",
    "urpe": "http://localhost:8004/urpe",
    "udoa": "agent://udoa",  # Route to agent
    "ceoa": "agent://ceoa",  # Route to agent
    "uie": "agent://uie"     # Route to agent
}
```

**3. ILE Observation Hooks**

Add ILE observation to all decision points:

```python
# In your existing engines (BUE, URPE)

from aetherion_agents import ILEAgent

ile = ILEAgent()

# After every decision
async def make_decision(query, context):
    result = await process(query, context)
    
    # Report to ILE
    await ile.observe_decision(decision)
    
    return result
```

## Month 1 Deployment Checklist

### Week 1: Agent Deployment

- [x] Install aetherion_agents package
- [x] Configure environment variables
- [x] Initialize all four agents
- [x] Verify Anthropic API connectivity
- [x] Run integration tests

### Week 2: Platform Integration

- [ ] Integrate agents with Cortex Gateway
- [ ] Update Function Broker routing
- [ ] Add ILE observation hooks to BUE
- [ ] Add ILE observation hooks to URPE
- [ ] Configure Constitutional Governance endpoints

### Week 3: Testing & Validation

- [ ] End-to-end testing with all engines
- [ ] Performance benchmarking
- [ ] Load testing (1000 requests)
- [ ] Error handling validation
- [ ] Constitutional Governance validation

### Week 4: Production Readiness

- [ ] Setup monitoring and alerting
- [ ] Configure logging
- [ ] Deploy to staging environment
- [ ] Run pilot with 2-3 test users
- [ ] Documentation complete
- [ ] Demo preparation

## Months 1-3: Learning Phase

### What to Monitor

**Agent Performance:**
- Decision latency (target: <5s p95)
- Confidence scores (target: >0.70 average)
- Governance approval rate (target: >90%)
- Child agent spawn count

**ILE Observations:**
- Query patterns identified
- Performance trends
- Optimization opportunities
- Agent collaboration patterns

**System Health:**
- Uptime (target: >99.9%)
- Error rate (target: <0.1%)
- API costs (monitor Anthropic usage)

### Weekly Reviews

Every week, review:
1. ILE pattern extraction results
2. Agent performance metrics
3. Customer feedback
4. Edge cases discovered
5. Optimization opportunities

### Pattern Collection Goals

By Month 3, ILE should have identified:
- ✓ 10+ common query patterns (per agent)
- ✓ 5+ optimal engine sequences
- ✓ 3+ performance optimizations
- ✓ 2+ confidence calibration insights

## Months 3-9: Production Build

Once patterns are validated, begin production build:

### UDOA Production (Months 3-5)
- Implement 12 validated query patterns
- Build 23 schema transformations
- Create 8 connector templates
- Deploy hybrid routing (production + agent)

### CEOA Production (Months 3-5)
- Implement 8 workload classifiers
- Build 8 placement strategies
- Create multi-cloud integration
- Deploy hybrid routing

### UIE Production (Months 5-7)
- Implement 5 response formats
- Build 7 orchestration patterns
- Create confidence scoring
- Deploy hybrid routing

### ILE Production (Months 5-7)
- Implement observation infrastructure
- Build pattern extraction engine
- Create feedback system
- Deploy hybrid routing

## Configuration Management

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."
export DATABASE_URL="postgresql://..."

# Optional (for UDOA)
export FRED_API_KEY="your-fred-key"
export WORLD_BANK_API_KEY="your-worldbank-key"

# Governance endpoints
export GOVERNANCE_ENDPOINT="http://localhost:8002/governance"
export ILE_ENDPOINT="http://localhost:8007/ile"
```

### Configuration File

Edit `config/agents_config.yaml` to customize:
- Model selection per agent
- Temperature and token limits
- Cloud provider configurations
- Data source connections
- Routing rules
- Monitoring thresholds

## Monitoring & Observability

### Metrics to Track

**Per Agent:**
```python
metrics = agent.get_metrics()
# Returns:
# {
#   "total_decisions": 150,
#   "avg_duration_ms": 2345.67,
#   "governance_approval_rate": 0.92,
#   "child_agents_spawned": 45
# }
```

**System-Wide:**
```python
health = await ile.get_system_health()
# Returns:
# {
#   "metrics": {
#     "ceoa": {...},
#     "uie": {...},
#     "udoa": {...},
#     "ile": {...}
#   },
#   "patterns_identified": 25,
#   "feedback_provided": 8
# }
```

### Logging

All agents use structured logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Logs include:
- Agent name
- Decision ID
- Query (truncated)
- Duration
- Confidence
- Governance result

### Alerting

Set up alerts for:
- Low confidence (<0.60): Investigation needed
- High latency (>10s): Performance issue
- High rejection rate (>10%): Governance issue
- Errors: System degradation

## Troubleshooting

### Common Issues

**Issue: "Module not found: anthropic"**
```bash
# Solution:
pip install anthropic>=0.8.0
```

**Issue: "Anthropic API key not found"**
```bash
# Solution:
export ANTHROPIC_API_KEY="your-key"
```

**Issue: "Agent timeout after 30s"**
```python
# Solution: Adjust timeout in agent initialization
agent = CEOAAgent(max_tokens=2000)  # Reduce tokens
```

**Issue: "Governance always rejects"**
```yaml
# Solution: Check governance configuration
governance:
  mode: "permissive"  # For testing
  benefit_threshold: 30  # Lower threshold
```

## Performance Optimization

### Reduce Latency

1. **Use smaller models for simple tasks:**
```python
ceoa = CEOAAgent(
    model="claude-haiku-3-5-20250422",  # Faster, cheaper
    max_tokens=2000
)
```

2. **Enable caching:**
```python
# Cache common transformations, schema mappings
```

3. **Parallel execution:**
```python
# UDOA spawns child agents in parallel
```

### Reduce Costs

1. **Route simple queries to production engines:**
```yaml
hybrid_routing:
  routing_rules:
    - query_pattern: "standard"
      route_to: "production"  # When available
```

2. **Use smaller context windows:**
```python
agent = UDOAAgent(max_tokens=2000)  # Instead of 4000
```

3. **Batch similar queries:**
```python
# Process multiple queries in one LLM call
```

## Security Considerations

### API Keys
- Never commit API keys to git
- Use environment variables or secrets manager
- Rotate keys regularly

### Data Privacy
- Agents don't store user data
- All data flows through Constitutional Governance
- Jurisdiction compliance enforced by UDOA

### Access Control
- Implement authentication on agent APIs
- Use RBAC for different user roles
- Audit all decisions via ILE

## Support

For questions or issues:
- Documentation: README.md (this directory)
- Integration examples: examples/complete_integration.py
- Configuration: config/agents_config.yaml
- Email: francoisjohnson94@icloud.com

## Next Steps

1. ✅ **Deploy agents** (Week 1)
2. ✅ **Integrate with platform** (Week 2-3)
3. ✅ **Begin learning phase** (Month 1-3)
4. ⏳ **Extract patterns** (Ongoing)
5. ⏳ **Build production engines** (Month 3-9)
6. ⏳ **Deploy hybrid architecture** (Month 9+)
7. ⏳ **Continuous improvement** (Forever)

**The agents are ready. Now it's time to deploy and learn.**
