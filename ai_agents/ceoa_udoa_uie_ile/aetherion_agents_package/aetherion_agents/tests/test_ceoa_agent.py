"""Tests for CEOA Agent"""

import pytest
from aetherion_agents import CEOAAgent


@pytest.mark.asyncio
async def test_ceoa_initialization():
    """Test CEOA agent initializes correctly"""
    ceoa = CEOAAgent()
    assert ceoa.agent_name == "CEOA"
    assert ceoa.cloud_providers is not None


@pytest.mark.asyncio
async def test_ceoa_workload_optimization():
    """Test CEOA workload optimization"""
    ceoa = CEOAAgent()
    
    result = await ceoa.optimize_placement(
        workload_description="Test workload",
        requirements={"type": "cpu-intensive"}
    )
    
    assert "placement" in result
    assert "confidence" in result
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_ceoa_metrics():
    """Test CEOA metrics tracking"""
    ceoa = CEOAAgent()
    
    # Make a decision
    await ceoa.optimize_placement(
        workload_description="Test workload",
        requirements={}
    )
    
    metrics = ceoa.get_metrics()
    assert metrics["total_decisions"] > 0
