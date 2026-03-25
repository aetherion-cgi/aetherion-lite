"""
API Models for UIE
Request and response structures for the single public endpoint
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from enum import Enum


class RequestFormat(str, Enum):
    """Format of incoming request"""
    NATURAL_LANGUAGE = "natural_language"
    STRUCTURED = "structured"


class AetherionRequest(BaseModel):
    """
    Universal request model for Aetherion.
    Accepts both natural language and structured requests.
    """
    # Natural language format
    message: Optional[str] = Field(None, description="Natural language request")
    
    # Structured format (legacy compatibility)
    capability: Optional[str] = Field(None, description="Direct capability invocation")
    params: Optional[Dict[str, Any]] = Field(None, description="Capability parameters")
    
    # Session management
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Context
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    jurisdiction: Optional[str] = Field(None, description="User's jurisdiction for governance")
    
    # Preferences
    response_format: Literal["conversational", "structured", "both"] = Field(
        default="conversational",
        description="How to format the response"
    )
    detail_level: Literal["minimal", "standard", "detailed", "expert"] = Field(
        default="standard",
        description="Level of detail in response"
    )
    
    # Streaming
    stream: bool = Field(default=False, description="Enable streaming response")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "message": "What happens if fusion energy becomes commercial by 2030?",
                    "session_id": "user-123-session-456",
                    "detail_level": "detailed"
                },
                {
                    "capability": "finance.underwrite",
                    "params": {
                        "deal": {
                            "type": "mining_project",
                            "capex": 100000000,
                            "jurisdiction": "US-AZ"
                        }
                    },
                    "response_format": "structured"
                }
            ]
        }


class IntentClassification(BaseModel):
    """Parsed intent from natural language"""
    purpose: str = Field(..., description="High-level purpose: underwrite, simulate, query, etc.")
    primary_capability: str = Field(..., description="Primary capability needed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")
    requires_clarification: bool = Field(default=False, description="Needs more info from user")
    clarification_questions: List[str] = Field(default_factory=list)


class ExecutionStep(BaseModel):
    """Single step in an execution plan"""
    step_number: int
    capability: str
    params: Dict[str, Any]
    is_critical: bool = Field(default=True, description="Fail entire plan if this fails")
    depends_on: List[int] = Field(default_factory=list, description="Step numbers this depends on")
    description: str = Field(..., description="Human-readable description")


class ExecutionPlan(BaseModel):
    """Multi-step execution plan"""
    steps: List[ExecutionStep]
    estimated_duration_seconds: float
    complexity_score: float = Field(..., description="0.0-1.0, used for governance")


class GovernanceDecision(BaseModel):
    """Governance authorization decision"""
    allowed: bool
    tier: Literal["T1", "T2", "T3", "HALT"]
    explanation: str
    review_id: Optional[str] = None
    restrictions: List[str] = Field(default_factory=list)


class CapabilityResult(BaseModel):
    """Result from a single capability invocation"""
    capability: str
    status: Literal["success", "error", "partial"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AetherionResponse(BaseModel):
    """
    Universal response model from Aetherion.
    Includes both conversational and structured data.
    """
    # Conversational response (primary for CustomGPT/Claude)
    message: str = Field(..., description="Human-readable response")
    
    # Structured data (optional, for API clients)
    data: Optional[Dict[str, Any]] = Field(None, description="Structured result data")
    
    # Metadata
    session_id: Optional[str] = Field(None, description="Session ID for follow-up")
    intent: Optional[IntentClassification] = Field(None, description="Parsed intent")
    execution_plan: Optional[ExecutionPlan] = Field(None, description="Execution plan used")
    governance: Optional[GovernanceDecision] = Field(None, description="Governance decision")
    
    # Execution info
    capabilities_used: List[str] = Field(default_factory=list)
    execution_time_ms: float = Field(..., description="Total execution time")
    
    # Status
    status: Literal["success", "partial", "error", "requires_review"] = Field(...)
    
    # Follow-up
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Suggested next questions")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Based on multi-domain analysis, commercialized fusion by 2030 would likely...",
                "data": {
                    "energy_market_impact": {"disruption_percentage": 15-30},
                    "materials_demand": {"copper_increase": 40, "lithium_decrease": 20}
                },
                "session_id": "user-123-session-456",
                "capabilities_used": ["intelligence.query", "intelligence.simulate"],
                "execution_time_ms": 28543.2,
                "status": "success",
                "follow_up_suggestions": [
                    "Would you like me to drill into energy market impacts?",
                    "Should I run sensitivity analysis with different timelines?"
                ]
            }
        }


class HealthStatus(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: str
    services: Dict[str, str] = Field(default_factory=dict, description="Status of dependent services")
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    support_reference: Optional[str] = None
