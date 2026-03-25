"""
Aetherion Common Schemas
Canonical request/response contracts for the integration fabric
"""

from pydantic import BaseModel, Field, validator, Extra
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
import uuid

from .enums import GovernanceTier, Region, EscalationTarget

class LearningEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    domain: Optional[str] = None   # or DomainType if you already have that enum in common
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GovernanceMetadata(BaseModel):
    """
    Constitutional governance metadata passed through all system calls.
    Ensures human primacy and transparent decision-making.
    """
    requested_tier: GovernanceTier = Field(
        default=GovernanceTier.AUTO,
        description="Requested authorization tier or auto-determination"
    )
    region: Region = Field(
        default=Region.US,
        description="Jurisdiction for policy enforcement"
    )
    pii_masking: bool = Field(
        default=True,
        description="Whether to mask personally identifiable information"
    )
    escalation_target: Optional[EscalationTarget] = Field(
        default=None,
        description="Target system for escalation if thresholds exceeded"
    )
    audit_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom tags for audit trail"
    )
    benefit_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="OPA-determined benefit score (0-1)"
    )
    harm_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="OPA-determined harm score (0-1)"
    )
    approval_required: bool = Field(
        default=False,
        description="Whether human approval is required"
    )

    class Config:
        use_enum_values = True


class Envelope(BaseModel):
    """
    Universal request envelope for all Aetherion operations.
    Carries intent, payload, policy context, and governance metadata.
    """
    tenant_id: str = Field(
        ...,
        description="Tenant identifier for multi-tenancy"
    )
    actor: str = Field(
        ...,
        description="Identity of the requesting actor (user, system, service)"
    )
    intent: Dict[str, Any] = Field(
        ...,
        description="High-level intent describing what the actor wants"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Specific data payload for the operation"
    )
    policy: Dict[str, Any] = Field(
        default_factory=dict,
        description="Policy context (constraints, rules, overrides)"
    )
    governance: GovernanceMetadata = Field(
        default_factory=GovernanceMetadata,
        description="Constitutional governance metadata"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (trace_id, session_id, etc.)"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Request timestamp"
    )

    @validator('intent', pre=True)
    @classmethod
    def validate_intent(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure intent has required fields"""
        if 'task' not in v:
            raise ValueError("Intent must include 'task' field")
        return v

    def with_governance(self, governance: GovernanceMetadata) -> 'Envelope':
        """Create a new envelope with updated governance metadata"""
        return self.model_copy(update={'governance': governance})

    def with_context(self, **context_updates: Any) -> 'Envelope':
        """Create a new envelope with updated context"""
        new_context = {**self.context, **context_updates}
        return self.model_copy(update={'context': new_context})


class NormalizedResult(BaseModel):
    """
    Universal response format for all Aetherion operations.
    Ensures consistent structure across all engines and adapters.
    """
    data: Any = Field(
        ...,
        description="Primary result data"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details, metrics, or metadata"
    )
    governance: Optional[GovernanceMetadata] = Field(
        default=None,
        description="Governance metadata from execution"
    )
    traces: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Execution traces for observability"
    )
    result_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique result identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Result timestamp"
    )
    success: bool = Field(
        default=True,
        description="Whether the operation succeeded"
    )
    error: Optional['ErrorDetail'] = Field(
        default=None,
        description="Error details if operation failed"
    )

    def is_success(self) -> bool:
        """Check if result represents a successful operation"""
        return self.success and self.error is None

    def with_trace(self, **trace_data: Any) -> 'NormalizedResult':
        """Add trace data to the result"""
        traces = self.traces or {}
        traces.update(trace_data)
        return self.model_copy(update={'traces': traces})


class ErrorDetail(BaseModel):
    """
    Sanitized error information that never exposes internal implementation.
    Critical for security: no stack traces, source code, or policy details.
    """
    code: str = Field(
        ...,
        description="Machine-readable error code"
    )
    message: str = Field(
        ...,
        description="Human-readable error message (sanitized)"
    )
    category: Literal["client", "server", "governance", "adapter", "timeout"] = Field(
        default="server",
        description="Error category for classification"
    )
    retryable: bool = Field(
        default=False,
        description="Whether the operation can be retried"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context (sanitized)"
    )

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        code: str = "INTERNAL_ERROR",
        category: str = "server",
        retryable: bool = False
    ) -> 'ErrorDetail':
        """
        Create sanitized error from exception.
        NEVER exposes raw exception messages or stack traces.
        """
        return cls(
            code=code,
            message="An error occurred during processing",
            category=category,
            retryable=retryable,
            details={"error_type": type(exc).__name__}
        )


class AuditRecord(BaseModel):
    """
    Immutable audit record for constitutional compliance.
    Forms blockchain-style audit trail.
    """
    record_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique audit record identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Audit event timestamp"
    )
    tenant_id: str = Field(
        ...,
        description="Tenant identifier"
    )
    actor: str = Field(
        ...,
        description="Actor who initiated the operation"
    )
    operation: str = Field(
        ...,
        description="Operation performed"
    )
    capability_id: Optional[str] = Field(
        default=None,
        description="Capability invoked"
    )
    governance: GovernanceMetadata = Field(
        ...,
        description="Governance metadata at time of operation"
    )
    result_success: bool = Field(
        ...,
        description="Whether operation succeeded"
    )
    benefit_score: Optional[float] = Field(
        default=None,
        description="Constitutional benefit score"
    )
    harm_score: Optional[float] = Field(
        default=None,
        description="Constitutional harm score"
    )
    approval_chain: List[str] = Field(
        default_factory=list,
        description="Chain of approval if human review required"
    )
    previous_hash: Optional[str] = Field(
        default=None,
        description="Hash of previous audit record for chaining"
    )
    record_hash: Optional[str] = Field(
        default=None,
        description="Hash of this record"
    )

    def compute_hash(self) -> str:
        """Compute hash for blockchain-style chaining"""
        import hashlib
        import json
        
        # Create deterministic representation
        record_data = {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "operation": self.operation,
            "result_success": self.result_success,
            "previous_hash": self.previous_hash
        }
        
        record_json = json.dumps(record_data, sort_keys=True)
        return hashlib.sha256(record_json.encode()).hexdigest()


# Enable forward references
NormalizedResult.update_forward_refs()