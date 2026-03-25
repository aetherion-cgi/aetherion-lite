# Aetherion AI Agents

Complete implementation of Aetherion's four AI agents: CEOA, UIE, UDOA, and ILE.

## Overview

This package implements Aetherion's agent-first development strategy, where AI agents are built first to validate requirements through real operation, then production engines are built based on proven patterns.

### The Four Agents

**1. CEOA (Compute & Energy Orchestration API)**
- Workload placement optimization across cloud providers
- Cost, carbon, and performance trade-off analysis
- Multi-cloud routing decisions
- Status: Agent implementation (Month 1-3 learning phase)

**2. UIE (Universal Intelligence Engine)**
- Multi-engine coordination and synthesis
- User-facing intelligence generation
- Response format adaptation
- Status: Agent implementation (Month 1-3 learning phase)

**3. UDOA (Universal Data Orchestration API)**
- Multi-source data integration
- Schema mapping and entity resolution
- Jurisdiction-compliant data routing
- Status: Agent implementation (Month 1-3 learning phase)

**4. ILE (Internal Learning Engine)**
- Meta-learning and pattern extraction
- Agent performance observation
- Feedback generation for continuous improvement
- Status: Agent implementation (Month 1-3 learning phase)

## Architecture

All agents inherit from `ConstitutionalAgent` base class, which provides:
- ✅ LLM integration (Anthropic Claude)
- ✅ Constitutional Governance validation
- ✅ Child agent spawning capability
- ✅ ILE observation integration
- ✅ Error handling and logging
- ✅ Performance metrics

```
ConstitutionalAgent (base)
├── CEOAAgent (compute orchestration)
├── UIEAgent (intelligence synthesis)
├── UDOAAgent (data orchestration)
└── ILEAgent (meta-learning)
```

## Installation

```bash
# Clone repository
git clone https://github.com/aetherion/aetherion-agents.git
cd aetherion-agents

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-api-key"
export DATABASE_URL="postgresql://..."
export FRED_API_KEY="your-fred-key"  # Optional

# Run tests
pytest tests/
```

## Quick Start

### Example 1: CEOA Workload Optimization

```python
from aetherion_agents.ceoa import CEOAAgent

# Initialize agent
ceoa = CEOAAgent()

# Optimize workload placement
result = await ceoa.optimize_placement(
    workload_description="Run Monte Carlo simulation with 10,000 iterations, "
                        "estimated 50GB memory, 8 CPU cores, 4 hours runtime",
    requirements={
        "type": "cpu-intensive",
        "max_cost_per_hour": 0.50,
        "optimize_carbon": True,
        "preferred_region": "us-east-1"
    }
)

print(f"Recommended placement: {result['placement']}")
print(f"Confidence: {result['confidence']}")
print(f"Governance approved: {result['governance_approved']}")
```

### Example 2: UIE Intelligence Synthesis

```python
from aetherion_agents.uie import UIEAgent

# Initialize agent
uie = UIEAgent()

# Synthesize intelligence from multiple engines
result = await uie.synthesize(
    query="Should we acquire Company X?",
    persona="executive",
    format_preference="executive_summary"
)

print(f"Synthesis: {result['synthesis']}")
print(f"Confidence: {result['confidence']}")
```

### Example 3: UDOA Data Discovery

```python
from aetherion_agents.udoa import UDOAAgent

# Initialize agent
udoa = UDOAAgent()

# Discover data across sources
result = await udoa.discover_data(
    query="What is the current GDP growth rate for the United States?",
    jurisdiction="US"
)

print(f"Data: {result['data']}")
print(f"Sources consulted: {result['data']['sources_consulted']}")
```

### Example 4: ILE Meta-Learning

```python
from aetherion_agents.ile import ILEAgent

# Initialize agent
ile = ILEAgent()

# Observe agent decisions (called automatically)
await ile.observe_decision(decision)

# Get system health
health = await ile.get_system_health()
print(f"System metrics: {health['metrics']}")

# Get agent feedback
feedback = await ile.get_agent_feedback("ceoa")
print(f"CEOA strengths: {feedback['strengths']}")
print(f"CEOA improvements: {feedback['improvements']}")

# Get identified patterns
patterns = await ile.get_patterns()
print(f"High priority patterns: {patterns['high_priority']}")
```

## Integration with Existing Platform

### Integration with BUE (Business Underwriting Engine)

```python
# UIE coordinates with BUE for business analysis
uie = UIEAgent()

result = await uie.synthesize(
    query="Analyze investment opportunity in quantum computing startup",
    persona="analyst"
)

# UIE internally:
# 1. Determines BUE is needed for business analysis
# 2. Calls BUE for financial assessment
# 3. Synthesizes BUE output with other context
# 4. Returns coherent narrative
```

### Integration with URPE (Universal Risk & Probabilistic Engine)

```python
# UIE coordinates with URPE for strategic analysis
result = await uie.synthesize(
    query="What are the geopolitical implications of US-China tech decoupling?",
    persona="strategic"
)

# UIE internally:
# 1. Determines URPE is needed for strategic/geopolitical analysis
# 2. Calls URPE for risk assessment
# 3. Synthesizes URPE output into user-friendly format
```

### Integration with Constitutional Governance

All agents automatically integrate with Constitutional Governance:

```python
# Every agent decision flows through governance
decision = await agent.make_decision(query, context)

# Governance evaluates:
# - Benefit score
# - Harm score
# - Authorization tier
# - Blind spots identified

# Decision includes governance result:
print(f"Governance tier: {decision.governance_score['tier']}")
print(f"Benefit: {decision.governance_score['benefit']}")
print(f"Harm: {decision.governance_score['harm']}")
```

## Configuration

Configuration is managed via `config/agents_config.yaml`:

```yaml
agents:
  global:
    model: "claude-sonnet-4-20250514"
    max_tokens: 4000
    temperature: 0.7
    governance_endpoint: "http://localhost:8002/governance"
    ile_endpoint: "http://localhost:8007/ile"
  
  ceoa:
    enabled: true
    cloud_providers:
      aws:
        enabled: true
        regions: ["us-east-1", "us-west-2"]
  
  # ... see agents_config.yaml for full configuration
```

## Hybrid Architecture (Production Engines + Agents)

Once production engines are built (Months 3-9), hybrid routing automatically distributes queries:

```yaml
hybrid_routing:
  enabled: true
  routing_rules:
    - query_pattern: "standard"
      confidence_threshold: 0.95
      route_to: "production"  # Fast, cheap production engine
    
    - query_pattern: "novel"
      route_to: "agent"  # Agent handles edge cases
    
    - query_pattern: "strategic"
      route_to: "agent"  # Agent for high-stakes decisions
```

### Benefits of Hybrid Architecture

**Performance:**
- 90% of queries → Production engines (microseconds, $0.0001/request)
- 10% of queries → AI agents (seconds, $0.01/request)
- Overall: Fast + intelligent

**Continuous Learning:**
- Agents discover new patterns
- ILE identifies patterns worth productionizing
- Engineering builds production implementation
- System continuously evolves

**Resilience:**
- Production engine fails → Fallback to agent
- Agent fails → Fallback to production
- Zero downtime during bugs/changes

## Child Agent Spawning

All agents can spawn specialized child agents for complex tasks:

```python
# Parent agent spawns children automatically
ceoa = CEOAAgent()

result = await ceoa.optimize_placement(
    workload_description="...",
    requirements={"optimize_cost": True, "optimize_carbon": True}
)

# CEOA internally spawned:
# - Cost optimizer child agent
# - Carbon optimizer child agent
# - Placement analyzer child agent

# Children work in parallel, return to parent
# Parent synthesizes results
```

## Monitoring & Observability

All agents expose performance metrics:

```python
# Get agent metrics
metrics = agent.get_metrics()

print(f"Total decisions: {metrics['total_decisions']}")
print(f"Avg duration: {metrics['avg_duration_ms']}ms")
print(f"Governance approval rate: {metrics['governance_approval_rate']}")
print(f"Child agents spawned: {metrics['child_agents_spawned']}")
```

ILE provides system-wide observability:

```python
ile = ILEAgent()

# System health
health = await ile.get_system_health()

# Agent-specific metrics
ceoa_metrics = health['metrics']['ceoa']
print(f"CEOA avg confidence: {ceoa_metrics['avg_confidence']}")
print(f"CEOA vs baseline: {ceoa_metrics['vs_baseline']}")
```

## Development Timeline

**Month 1 (Weeks 1-4): Agent Build**
- Week 1: CEOA + UDOA agents
- Week 2: UIE + ILE agents
- Week 3: Integration testing
- Week 4: Demo preparation
- **Deliverable:** All 4 agents operational

**Months 1-3 (Weeks 5-12): Learning Period**
- Agents handle all production workload
- ILE observes and extracts patterns
- Pilot customers provide validation
- **Deliverable:** Validated patterns for production build

**Months 3-9 (Weeks 13-36): Production Build**
- Build production engines based on proven patterns
- Implement hybrid routing (production + agents)
- **Deliverable:** Production-optimized platform

**Month 9+: Hybrid Forever**
- Production handles 90% (fast, cheap)
- Agents handle 10% (edge cases, strategic)
- Continuous learning via ILE
- **Deliverable:** Self-improving platform

## API Reference

### ConstitutionalAgent (Base Class)

```python
class ConstitutionalAgent:
    def __init__(
        self,
        agent_name: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4000,
        temperature: float = 0.7
    )
    
    async def make_decision(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> AgentDecision
    
    async def reason(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]
    
    async def spawn_child_agent(
        self,
        child_type: str,
        task: str,
        context: Dict[str, Any]
    ) -> Any
    
    def get_metrics(self) -> Dict[str, Any]
```

### CEOAAgent

```python
class CEOAAgent(ConstitutionalAgent):
    async def optimize_placement(
        self,
        workload_description: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]
```

### UIEAgent

```python
class UIEAgent(ConstitutionalAgent):
    async def synthesize(
        self,
        query: str,
        persona: str = "analyst",
        format_preference: Optional[str] = None
    ) -> Dict[str, Any]
```

### UDOAAgent

```python
class UDOAAgent(ConstitutionalAgent):
    async def discover_data(
        self,
        query: str,
        jurisdiction: str = "US"
    ) -> Dict[str, Any]
```

### ILEAgent

```python
class ILEAgent(ConstitutionalAgent):
    async def observe_decision(
        self, 
        decision: AgentDecision
    ) -> None
    
    async def get_system_health(self) -> Dict[str, Any]
    
    async def get_agent_feedback(
        self, 
        agent_name: str
    ) -> Dict[str, Any]
    
    async def get_patterns(self) -> Dict[str, Any]
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific agent tests
pytest tests/test_ceoa_agent.py
pytest tests/test_uie_agent.py
pytest tests/test_udoa_agent.py
pytest tests/test_ile_agent.py

# Run with coverage
pytest --cov=aetherion_agents tests/

# Run integration tests
pytest tests/test_integration.py
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

Proprietary - Aetherion, LLC

## Contact

**Aetherion Architecture Team**
- Email: francoisjohnson94@icloud.com
- Documentation: https://docs.aetherion.ai

## Appendix: Agent-First Strategy

This implementation follows Aetherion's revolutionary agent-first development strategy:

**Traditional Approach:**
```
Spec (6 months) → Build (18 months) → Launch → Hope it works
Risk: High | Cost: $11.7M | Time: 24 months
```

**Aetherion Approach:**
```
Agents (1 month) → Learn (3 months) → Build production (6 months) → Scale
Risk: Low | Cost: $2.2M | Time: 9 months
```

**Why This Works:**
1. ✅ Validate requirements through real operation
2. ✅ Build production based on proven patterns
3. ✅ Hybrid architecture provides resilience
4. ✅ Continuous learning via ILE
5. ✅ 2-4 year competitive moat

See `docs/agent-first-strategy.md` for full details.
