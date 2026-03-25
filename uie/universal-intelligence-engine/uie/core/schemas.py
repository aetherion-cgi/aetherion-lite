"""
Model-IO Contract: Envelope and NormalizedResult schemas.

This defines the single contract for all UIE interactions:
- Envelope: What comes into UIE
- NormalizedResult: What UIE returns
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


# ============================================================================
# ENVELOPE (Request Schema)
# ============================================================================

class Intent(BaseModel):
    """What the user wants to accomplish."""
    
    task: str = Field(
        ...,
        description="High-level task type: query, analysis, action, etc."
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Relevant domains: finance, healthcare, engineering, etc."
    )
    sensitivity: Literal["public", "internal", "confidential", "restricted"] = Field(
        default="internal",
        description="Data sensitivity level for policy enforcement"
    )
    latency_slo: float = Field(
        default=1.5,
        description="Target response time in seconds",
        ge=0.1,
        le=30.0
    )


class ContextRef(BaseModel):
    """Reference to external data without including it in payload."""
    
    ref_type: str = Field(..., description="Type: document_id, url, dataset_id, etc.")
    ref_value: str = Field(..., description="The actual reference value")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class Payload(BaseModel):
    """The actual content of the request."""
    
    text: Optional[str] = Field(None, description="Text content")
    json_data: Optional[Dict[str, Any]] = Field(None, description="Structured data")
    media_refs: List[ContextRef] = Field(
        default_factory=list,
        description="References to images, videos, audio"
    )
    
    @validator('text', 'json_data')
    def at_least_one_content(cls, v, values):
        """Ensure at least one of text or json_data is provided."""
        if not v and not values.get('json_data') and not values.get('text'):
            raise ValueError("Must provide at least text or json_data")
        return v


class ToolPlanStep(BaseModel):
    """A step in the tool execution plan."""
    
    tool_name: str = Field(..., description="Name from Tool Catalog")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(
        default_factory=list,
        description="IDs of steps this depends on"
    )
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class Limits(BaseModel):
    """Resource limits for this request."""
    
    max_tokens: int = Field(default=4000, description="Max tokens in response")
    max_tool_calls: int = Field(default=10, description="Max tool invocations")
    timeout_seconds: float = Field(default=30.0, description="Max execution time")


class Preferences(BaseModel):
    """User preferences for response formatting."""
    
    response_format: Literal["text", "json", "xml", "markdown"] = "text"
    include_citations: bool = True
    include_reasoning: bool = False  # Never expose chain-of-thought
    verbosity: Literal["concise", "normal", "detailed"] = "normal"


class Policy(BaseModel):
    """Policy constraints for this request."""
    
    region: Literal["US", "EU", "ROW"] = Field(
        default="US",
        description="Geographic region for residency requirements"
    )
    allowed_tools: Optional[List[str]] = Field(
        None,
        description="Whitelist of allowed tools. None = all allowed"
    )
    pii_masking: bool = Field(
        default=True,
        description="Whether to mask PII in responses"
    )
    data_retention_days: int = Field(
        default=90,
        description="How long to retain this request/response"
    )


class Trace(BaseModel):
    """Tracing information for observability."""
    
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = Field(default_factory=dict)


class Envelope(BaseModel):
    """
    The universal request envelope for UIE.
    
    This is the ONLY contract UIE accepts. All requests must conform to this schema.
    """
    
    # Identity
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant making the request")
    actor: str = Field(..., description="User or service making the request")
    
    # Intent & Context
    intent: Intent
    context_refs: List[ContextRef] = Field(
        default_factory=list,
        description="References to context without including full data"
    )
    payload: Payload
    
    # Execution Plan
    tool_plan: List[ToolPlanStep] = Field(
        default_factory=list,
        description="Optional pre-computed tool plan. If empty, UIE computes it."
    )
    
    # Constraints
    limits: Limits = Field(default_factory=Limits)
    preferences: Preferences = Field(default_factory=Preferences)
    policy: Policy = Field(default_factory=Policy)
    
    # Observability
    trace: Trace = Field(default_factory=Trace)
    
    # Continuation (for clarification loop)
    thread_id: Optional[str] = Field(
        None,
        description="If continuing a previous request, the thread ID"
    )
    continuation_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Data from previous clarification"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# NORMALIZED RESULT (Response Schema)
# ============================================================================

class Citation(BaseModel):
    """A citation for a claim in the response."""
    
    source: str = Field(..., description="Source identifier (document_id, url, etc.)")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt (if applicable)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: Optional[datetime] = None


class ToolCall(BaseModel):
    """Record of a tool call made during processing."""
    
    tool_name: str
    parameters: Dict[str, Any]
    result_summary: str = Field(..., description="Summary of tool result")
    duration_ms: float
    success: bool


class SafetyFlag(BaseModel):
    """Safety or content moderation flag."""
    
    flag_type: str = Field(..., description="Type of safety concern")
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    auto_remediated: bool = Field(
        default=False,
        description="Whether UIE auto-fixed the issue"
    )


class Usage(BaseModel):
    """Resource usage for this request."""
    
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: int
    duration_ms: float
    cost_usd: Optional[float] = None


class StructuredOutput(BaseModel):
    """Optional structured output if schema was requested."""
    
    schema_name: str
    data: Dict[str, Any]
    validation_passed: bool


class ClarificationRequest(BaseModel):
    """Request for clarification from the user."""
    
    question: str = Field(..., description="Question to ask the user")
    fields_needed: List[str] = Field(
        default_factory=list,
        description="Specific fields that need clarification"
    )
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID for continuing this conversation"
    )
    ttl_seconds: int = Field(
        default=300,
        description="How long this clarification is valid"
    )


class NormalizedResult(BaseModel):
    """
    The universal response from UIE.
    
    This is the ONLY format UIE returns. All responses conform to this schema.
    """
    
    # Identity
    request_id: str
    trace_id: str
    
    # Status
    status: Literal["completed", "clarify", "error", "partial"] = Field(
        ...,
        description="Completion status of the request"
    )
    
    # Content
    final_text: Optional[str] = Field(
        None,
        description="The final text response (always present for completed)"
    )
    structured: Optional[StructuredOutput] = Field(
        None,
        description="Structured output if schema was requested"
    )
    
    # Provenance
    citations: List[Citation] = Field(
        default_factory=list,
        description="Citations for claims in final_text"
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Tools invoked during processing"
    )
    
    # Safety & Policy
    safety_flags: List[SafetyFlag] = Field(
        default_factory=list,
        description="Any safety concerns identified"
    )
    policy_digest: str = Field(
        ...,
        description="Hash of policy bundle used for audit trail"
    )
    
    # Metadata
    usage: Usage
    
    # Clarification (if status = "clarify")
    clarification: Optional[ClarificationRequest] = None
    
    # Error (if status = "error")
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Timestamps
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('final_text')
    def validate_completed_has_text(cls, v, values):
        """If status is completed, final_text must be present."""
        if values.get('status') == 'completed' and not v:
            raise ValueError("Completed responses must include final_text")
        return v
    
    @validator('clarification')
    def validate_clarify_has_request(cls, v, values):
        """If status is clarify, clarification must be present."""
        if values.get('status') == 'clarify' and not v:
            raise ValueError("Clarify responses must include clarification")
        return v


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_envelope(data: Dict[str, Any]) -> Envelope:
    """
    Validate and parse an envelope from raw data.
    
    Raises:
        ValidationError: If envelope is invalid
    """
    return Envelope(**data)


def create_normalized_result(
    request_id: str,
    trace_id: str,
    status: str,
    policy_digest: str,
    usage: Usage,
    **kwargs
) -> NormalizedResult:
    """
    Factory function for creating NormalizedResult with required fields.
    """
    return NormalizedResult(
        request_id=request_id,
        trace_id=trace_id,
        status=status,
        policy_digest=policy_digest,
        usage=usage,
        **kwargs
    )
