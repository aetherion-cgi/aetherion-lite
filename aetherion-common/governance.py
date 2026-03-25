"""
Aetherion Governance Binding
Central entrypoint for constitutional governance across all modules.
Every ecosystem (9-lane, agents, wrappers) is subordinate to constitutional-governance.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import os

# Canonical governance root
GOVERNANCE_ROOT = Path(__file__).resolve().parents[1] / "constitutional-governance"


def load_policies() -> Dict[str, Any]:
    """
    Returns governance configuration and file paths.
    Used by OPA or internal policy checks.
    
    Returns:
        dict: Governance configuration with paths and policies
    """
    return {
        "root": GOVERNANCE_ROOT,
        "policies_path": GOVERNANCE_ROOT / "policies",
        "articles_path": GOVERNANCE_ROOT / "articles",
        "enabled": os.getenv("GOVERNANCE_ENABLED", "true").lower() == "true",
    }


def check_policy_compliance(action: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Check if an action complies with governance policies.
    
    Args:
        action: The action being performed (e.g., "finance.underwrite", "compute.dispatch")
        context: Context data for the action (deal data, job specs, etc.)
    
    Returns:
        tuple: (is_compliant, reason_if_not_compliant)
    """
    policies = load_policies()
    
    if not policies["enabled"]:
        return True, None
    
    # Placeholder for actual policy evaluation
    # In production, this would interface with OPA or internal policy engine
    # For now, we ensure the governance system is acknowledged
    
    return True, None


def validate_engine_operation(engine_name: str, operation: str, params: Dict[str, Any]) -> bool:
    """
    Validate that an engine operation complies with governance rules.
    
    Args:
        engine_name: Name of the engine (BUE, CEOA, UDOA, UIE, ILE, DomainCortex)
        operation: Operation being performed
        params: Operation parameters
    
    Returns:
        bool: True if operation is valid
    """
    is_compliant, reason = check_policy_compliance(
        f"{engine_name.lower()}.{operation}",
        params
    )
    
    if not is_compliant:
        raise ValueError(f"Governance violation: {reason}")
    
    return True
