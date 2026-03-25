"""
Aetherion Common Enumerations
Standard enums used across the Aetherion integration fabric
"""

from enum import Enum

class DomainType(str, Enum):
    TASK_BASED = "task_based"
    INTERNET_LEARNING = "internet_learning"
    INFRASTRUCTURE = "infrastructure"
    DOMAIN_CORTEX = "DOMAIN_CORTEX"


class GovernanceTier(str, Enum):
    """Constitutional governance authorization tiers"""
    AUTO = "auto"  # Let OPA determine tier
    T1 = "T1"  # 90-100% autonomous
    T2 = "T2"  # 70-90% international review
    T3 = "T3"  # 50-70% critical review
    HALT = "halt"  # <50% immediate halt


class Region(str, Enum):
    """Geographic regions for jurisdiction-specific governance"""
    US = "US"
    EU = "EU"
    ROW = "ROW"  # Rest of World


class EscalationTarget(str, Enum):
    """Valid escalation targets for scenarios exceeding thresholds"""
    URPE = "URPE"
    DOMAIN_CORTEX = "DOMAIN_CORTEX"


class AdapterType(str, Enum):
    """Adapter communication protocols"""
    HTTP = "http"
    KAFKA = "kafka"
    GRPC = "grpc"


class IntentTask(str, Enum):
    """High-level task types for routing"""
    QUERY = "query"
    ANALYSIS = "analysis"
    UNDERWRITING = "underwriting"
    SCHEDULING = "scheduling"
    DATA_FETCH = "data_fetch"
    EVALUATION = "evaluation"
    SYNTHESIS = "synthesis"


class Domain(str, Enum):
    """Domain classifications for capability routing"""
    GENERAL = "general"
    FINANCE = "finance"
    CREDIT_RISK = "credit_risk"
    DATA = "data"
    COMPUTE = "compute"
    ENERGY = "energy"
    STRATEGY = "strategy"
    GOVERNANCE = "governance"
    ORCHESTRATION = "orchestration"
    MILITARY = "military"
    EXISTENTIAL = "existential"
