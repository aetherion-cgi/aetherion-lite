"""
Aetherion AI Agents Package
Parent and child agent ecosystems for each core engine.
"""
from .agent_registry import AgentRegistry, get_registry

__all__ = [
    "AgentRegistry",
    "get_registry",
]
