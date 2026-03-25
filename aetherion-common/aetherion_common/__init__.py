"""
Aetherion Common Schemas Package
Shared data models and enums for Aetherion integration fabric
"""

from .schemas import (
    GovernanceMetadata,
    Envelope,
    NormalizedResult,
    ErrorDetail,
    AuditRecord
)
from .enums import (
    GovernanceTier,
    Region,
    EscalationTarget,
    AdapterType
)

__version__ = "1.0.0"

__all__ = [
    "GovernanceMetadata",
    "Envelope",
    "NormalizedResult",
    "ErrorDetail",
    "AuditRecord",
    "GovernanceTier",
    "Region",
    "EscalationTarget",
    "AdapterType",
]
