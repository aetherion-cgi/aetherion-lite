"""
Aetherion AI Agents

Complete implementation of Aetherion's four AI agents:
- CEOA: Compute & Energy Orchestration
- UIE: Universal Intelligence Engine
- UDOA: Universal Data Orchestration
- ILE: Internal Learning Engine
"""

from .ceoa import CEOAAgent
from .uie import UIEAgent
from .udoa import UDOAAgent
from .ile import ILEAgent

__version__ = "1.0.0"
__all__ = ["CEOAAgent", "UIEAgent", "UDOAAgent", "ILEAgent"]
