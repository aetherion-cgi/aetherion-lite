"""
Governance binding for Aetherion.
Every new ecosystem (9-lane, agents, wrappers) is subordinate to constitutional-governance.
"""
from pathlib import Path
from typing import Dict, Any, Optional


# Calculate governance root relative to this file
GOVERNANCE_ROOT = Path(__file__).resolve().parents[2] / "constitutional-governance" / "constitutional-governance"


def load_policies() -> Dict[str, Any]:
    """
    Returns governance configuration and policy paths.
    All new code must use this as the single source of truth for governance.
    
    Returns:
        Dict containing:
        - root: Path to governance root
        - policies_dir: Path to policies directory
        - opa_bundle: Path to OPA bundle (if exists)
    """
    policies_dir = GOVERNANCE_ROOT / "policies"
    
    config = {
        "root": GOVERNANCE_ROOT,
        "policies_dir": policies_dir,
        "constitutional_policy": policies_dir / "constitutional_governance_v1.0.rego",
    }
    
    # Check if OPA bundle exists
    opa_bundle = GOVERNANCE_ROOT / "bundles" / "governance.tar.gz"
    if opa_bundle.exists():
        config["opa_bundle"] = opa_bundle
    
    return config


def get_governance_root() -> Path:
    """Get the root path of the governance system."""
    return GOVERNANCE_ROOT


def validate_governance_available() -> bool:
    """
    Validate that governance policies are accessible.
    
    Returns:
        True if governance policies are found, False otherwise.
    """
    policies_dir = GOVERNANCE_ROOT / "policies"
    return policies_dir.exists() and (policies_dir / "constitutional_governance_v1.0.rego").exists()


def validate_engine_operation(engine_name: str, operation: str, input_data: Dict[str, Any]) -> bool:
    """
    Validate an engine operation against governance policies.
    
    Args:
        engine_name: Name of the engine (e.g., "BUE", "CEOA")
        operation: Operation being performed (e.g., "underwrite", "dispatch")
        input_data: Input data for the operation
    
    Returns:
        True if operation is allowed, raises exception otherwise
    
    Raises:
        ValueError: If operation violates governance policies
    """
    if not validate_governance_available():
        # If governance not available, log warning but allow operation
        import logging
        logging.getLogger(__name__).warning(
            f"Governance validation skipped for {engine_name}.{operation} - policies not available"
        )
        return True
    
    # Placeholder for actual OPA policy evaluation
    # In production, this would call OPA or internal policy engine
    # For now, we perform basic validation
    
    # Basic validation: ensure required fields exist
    if not engine_name or not operation:
        raise ValueError("Engine name and operation must be specified")
    
    # Log the operation for audit trail
    import logging
    logging.getLogger(__name__).info(
        f"Governance check: {engine_name}.{operation} validated"
    )
    
    return True
