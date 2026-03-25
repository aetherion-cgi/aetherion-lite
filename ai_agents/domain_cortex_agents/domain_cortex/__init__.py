"""
Aetherion Domain Cortex
30 AI Agents for Industry and Technology Domains
"""

__version__ = "1.0.0"
__author__ = "Aetherion, LLC"

from domain_cortex.base.domain_agent import DomainAgent, ChildDomainAgent
from domain_cortex.base.router import DomainOrchestrator, DomainRegistry, DomainRouter
from domain_cortex.base.engine_clients import (
    BUEClient, URPEClient, UIEClient, UDOAClient, CEOAClient, ILEClient
)

__all__ = [
    'DomainAgent',
    'ChildDomainAgent',
    'DomainOrchestrator',
    'DomainRegistry',
    'DomainRouter',
    'BUEClient',
    'URPEClient',
    'UIEClient',
    'UDOAClient',
    'CEOAClient',
    'ILEClient',
]
