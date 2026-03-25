"""
OPA (Open Policy Agent) Integration

Enforces security policies at ingress and egress:
- Pre-call: Residency requirements, PII masking, authorization
- Pre-publish: Final redaction, data minimization, audit logging

Zero-trust architecture: Deny by default, explicit allow only.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import httpx
import hashlib
import json
from datetime import datetime

from uie.core.schemas import Envelope, NormalizedResult, Policy


class PolicyDecision(str, Enum):
    """OPA policy decision."""
    ALLOW = "allow"
    DENY = "deny"
    MASK = "mask"  # Allow but mask certain fields


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    policy_digest: str  # Hash of policy bundle for audit trail
    violations: List[str]  # List of policy violations (if any)
    masked_fields: List[str]  # Fields that were masked
    reasoning: Optional[str] = None  # Why decision was made


class OPAClient:
    """
    Client for Open Policy Agent.
    
    Communicates with OPA server to evaluate policies.
    """
    
    def __init__(self, opa_url: str = "http://opa:8181"):
        self.opa_url = opa_url
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def evaluate(
        self,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a policy against input data.
        
        Args:
            policy_path: Path to policy (e.g., "aetherion/uie/ingress")
            input_data: Data to evaluate
        
        Returns:
            OPA decision result
        """
        url = f"{self.opa_url}/v1/data/{policy_path}"
        
        response = await self.client.post(
            url,
            json={"input": input_data}
        )
        response.raise_for_status()
        
        return response.json()
    
    async def get_bundle_digest(self) -> str:
        """Get hash of currently loaded policy bundle."""
        response = await self.client.get(f"{self.opa_url}/v1/policies")
        response.raise_for_status()
        
        policies = response.json()
        policy_hash = hashlib.sha256(
            json.dumps(policies, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return policy_hash
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class PolicyEnforcer:
    """
    Enforces policies using OPA.
    
    Two checkpoints:
    1. Pre-call (ingress): Before processing request
    2. Pre-publish (egress): Before returning response
    """
    
    def __init__(self, opa_client: OPAClient):
        self.opa = opa_client
    
    async def enforce_ingress(self, envelope: Envelope) -> PolicyResult:
        """
        Enforce ingress policies.
        
        Checks:
        - Data residency requirements
        - PII masking requirements
        - Authorization (tenant/actor)
        - Rate limits
        - Allowed tools
        
        Returns:
            PolicyResult with decision and any masking needed
        """
        # Prepare input for OPA
        input_data = {
            "tenant_id": envelope.tenant_id,
            "actor": envelope.actor,
            "intent": {
                "task": envelope.intent.task,
                "domains": envelope.intent.domains,
                "sensitivity": envelope.intent.sensitivity
            },
            "policy": {
                "region": envelope.policy.region,
                "pii_masking": envelope.policy.pii_masking
            },
            "payload": {
                "has_text": envelope.payload.text is not None,
                "has_json": envelope.payload.json_data is not None,
                "has_media": len(envelope.payload.media_refs) > 0
            },
            "tool_plan": [step.tool_name for step in envelope.tool_plan],
            "timestamp": envelope.created_at.isoformat()
        }
        
        # Evaluate policy
        result = await self.opa.evaluate("aetherion/uie/ingress", input_data)
        
        # Parse result
        decision_data = result.get("result", {})
        
        decision = PolicyDecision.DENY
        if decision_data.get("allow", False):
            decision = PolicyDecision.ALLOW
        elif decision_data.get("allow_with_masking", False):
            decision = PolicyDecision.MASK
        
        # Get policy digest
        policy_digest = await self.opa.get_bundle_digest()
        
        return PolicyResult(
            decision=decision,
            policy_digest=policy_digest,
            violations=decision_data.get("violations", []),
            masked_fields=decision_data.get("mask_fields", []),
            reasoning=decision_data.get("reasoning")
        )
    
    async def enforce_egress(
        self,
        envelope: Envelope,
        result: NormalizedResult
    ) -> PolicyResult:
        """
        Enforce egress policies.
        
        Checks:
        - Final PII redaction
        - Data minimization
        - Citation requirements
        - Safety flags
        
        Returns:
            PolicyResult with any additional masking needed
        """
        # Prepare input for OPA
        input_data = {
            "tenant_id": envelope.tenant_id,
            "actor": envelope.actor,
            "policy": {
                "region": envelope.policy.region,
                "pii_masking": envelope.policy.pii_masking,
                "data_retention_days": envelope.policy.data_retention_days
            },
            "result": {
                "status": result.status,
                "has_final_text": result.final_text is not None,
                "has_structured": result.structured is not None,
                "citation_count": len(result.citations),
                "safety_flag_count": len(result.safety_flags),
                "safety_severity": max(
                    [f.severity for f in result.safety_flags],
                    default="low"
                )
            }
        }
        
        # Evaluate policy
        opa_result = await self.opa.evaluate("aetherion/uie/egress", input_data)
        
        # Parse result
        decision_data = opa_result.get("result", {})
        
        decision = PolicyDecision.DENY
        if decision_data.get("allow", False):
            decision = PolicyDecision.ALLOW
        elif decision_data.get("allow_with_masking", False):
            decision = PolicyDecision.MASK
        
        return PolicyResult(
            decision=decision,
            policy_digest=result.policy_digest,  # Use existing digest
            violations=decision_data.get("violations", []),
            masked_fields=decision_data.get("mask_fields", []),
            reasoning=decision_data.get("reasoning")
        )
    
    def apply_masking(
        self,
        envelope: Envelope,
        masked_fields: List[str]
    ) -> Envelope:
        """
        Apply masking to envelope based on policy.
        
        Masks PII and sensitive data in place.
        """
        # Mask text if needed
        if "payload.text" in masked_fields and envelope.payload.text:
            envelope.payload.text = self._mask_pii(envelope.payload.text)
        
        # Mask JSON if needed
        if "payload.json_data" in masked_fields and envelope.payload.json_data:
            envelope.payload.json_data = self._mask_dict(
                envelope.payload.json_data
            )
        
        return envelope
    
    def apply_redaction(
        self,
        result: NormalizedResult,
        masked_fields: List[str]
    ) -> NormalizedResult:
        """
        Apply final redaction to result based on policy.
        """
        # Redact final text if needed
        if "final_text" in masked_fields and result.final_text:
            result.final_text = self._mask_pii(result.final_text)
        
        # Redact structured output if needed
        if "structured" in masked_fields and result.structured:
            result.structured.data = self._mask_dict(result.structured.data)
        
        return result
    
    def _mask_pii(self, text: str) -> str:
        """
        Mask PII in text.
        
        Simple masking for:
        - Email addresses
        - Phone numbers
        - SSN patterns
        - Credit card patterns
        """
        import re
        
        # Email
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            text
        )
        
        # Phone (US format)
        text = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE]',
            text
        )
        
        # SSN
        text = re.sub(
            r'\b\d{3}-\d{2}-\d{4}\b',
            '[SSN]',
            text
        )
        
        # Credit card (basic pattern)
        text = re.sub(
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            '[CARD]',
            text
        )
        
        return text
    
    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask PII in dictionary."""
        masked = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                masked[key] = self._mask_pii(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    self._mask_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        
        return masked


# ============================================================================
# REGION-SPECIFIC POLICIES
# ============================================================================

class RegionalPolicyManager:
    """
    Manages region-specific policy bundles.
    
    Different regions (US, EU, ROW) have different requirements:
    - US: HIPAA, SOC2
    - EU: GDPR
    - ROW: Local regulations
    """
    
    def __init__(self):
        self.policy_bundles = {
            "US": {
                "pii_masking_required": True,
                "data_retention_max_days": 2555,  # 7 years for HIPAA
                "audit_required": True,
                "encryption_at_rest": True
            },
            "EU": {
                "pii_masking_required": True,
                "data_retention_max_days": 90,  # GDPR default
                "audit_required": True,
                "encryption_at_rest": True,
                "right_to_deletion": True
            },
            "ROW": {
                "pii_masking_required": False,
                "data_retention_max_days": 365,
                "audit_required": False,
                "encryption_at_rest": True
            }
        }
    
    def get_policy(self, region: str) -> Dict[str, Any]:
        """Get policy bundle for region."""
        return self.policy_bundles.get(region, self.policy_bundles["ROW"])
    
    def validate_policy(self, policy: Policy) -> bool:
        """Validate that policy meets regional requirements."""
        regional = self.get_policy(policy.region)
        
        # Check retention
        if policy.data_retention_days > regional["data_retention_max_days"]:
            return False
        
        # Check masking requirement
        if regional["pii_masking_required"] and not policy.pii_masking:
            return False
        
        return True
