# Quick Start Guide - Aetherion AI Agents

## Installation (5 Minutes)

```bash
# Install from source
cd aetherion_agents_package
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

## Set Environment Variables

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

## Basic Usage

### Example 1: CEOA Workload Optimization

```python
import asyncio
from aetherion_agents import CEOAAgent

async def main():
    # Initialize agent
    ceoa = CEOAAgent()
    
    # Optimize workload placement
    result = await ceoa.optimize_placement(
        workload_description="Monte Carlo simulation, 50GB RAM, 8 cores, 4 hours",
        requirements={
            "type": "cpu-intensive",
            "max_cost_per_hour": 0.50,
            "optimize_carbon": True
        }
    )
    
    print(f"Recommended: {result['placement']}")
    print(f"Confidence: {result['confidence']}")

asyncio.run(main())
```

### Example 2: UIE Intelligence Synthesis

```python
from aetherion_agents import UIEAgent

async def main():
    uie = UIEAgent()
    
    result = await uie.synthesize(
        query="Should we acquire Company X?",
        persona="executive"
    )
    
    print(result['synthesis'])

asyncio.run(main())
```

### Example 3: Complete Integration

```python
# Run the complete integration example
python aetherion_agents/examples/complete_integration.py
```

## Next Steps

1. Read full documentation: `docs/DEPLOYMENT.md`
2. Explore configuration: `config/agents_config.yaml`
3. Run integration tests: `pytest tests/`
4. Start building with agents!

## Support

- Documentation: See README.md and docs/
- Examples: See examples/
- Email: francoisjohnson94@icloud.com
