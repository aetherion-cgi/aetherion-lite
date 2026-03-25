"""
Internal Learning Engine - Core Data Models

Comprehensive data structures for the ILE system using Pydantic for validation.
All learning events, decisions, and knowledge representations flow through these models.

Author: Aetherion Development Team
Date: November 15, 2025
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS - Type-safe constants
# ============================================================================

class DomainType(str, Enum):
    """Learning domain categories"""
    TASK_BASED = "task_based"  # Domain 1: Learn from task outcomes
    INTERNET = "internet"  # Domain 2: Learn from web
    USER_INTERACTION = "user_interaction"  # Domain 3: Learn from user behavior
    CROSS_DOMAIN = "cross_domain"  # Domain 4: Cross-domain synthesis
    FEDERATED_EDGE = "federated_edge"  # Domain 5: Edge device learning
    MULTI_LLM = "multi_llm"  # Domain 6: Multi-LLM coordination
    SECURITY = "security"  # Domain 7: Function broker security
    DOMAIN_CORTEX = "domain_cortex"  # Meta-learning layer


class APIType(str, Enum):
    """Aetherion API types"""
    BUE = "bue"  # Business Underwriting Engine
    URPE = "urpe"  # Universal Risk & Probabilistic Engine
    UDOA = "udoa"  # Universal Data Orchestration API
    CEOA = "ceoa"  # Compute Energy Orchestration API
    UIE = "uie"  # Universal Intelligence Engine


class LearningEventType(str, Enum):
    """Types of learning events"""
    OUTCOME = "outcome"  # Task outcome (prediction vs actual)
    PATTERN = "pattern"  # Discovered pattern
    KNOWLEDGE = "knowledge"  # New knowledge extracted
    FEEDBACK = "feedback"  # User feedback
    SYNTHESIS = "synthesis"  # Cross-domain synthesis
    UPDATE = "update"  # Model update
    ANOMALY = "anomaly"  # Anomaly detection
    SECURITY = "security"  # Security event


class ConstitutionalDecision(str, Enum):
    """Constitutional governance decisions"""
    APPROVED = "approved"  # Fully approved for implementation
    REVIEW_REQUIRED = "review_required"  # Requires human review
    REJECTED = "rejected"  # Rejected for constitutional violations


class Jurisdiction(str, Enum):
    """Deployment jurisdictions"""
    SANDBOX = "sandbox"  # Testing environment
    NATO = "nato"  # NATO member states
    GLOBAL = "global"  # Global deployment
    EU = "eu"  # European Union
    US = "us"  # United States


# ============================================================================
# LEARNING EVENT MODELS
# ============================================================================

class LearningEvent(BaseModel):
    """
    Core learning event structure. All learning in ILE flows through this model.
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_type: LearningEventType
    domain: DomainType
    api: APIType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event data
    prediction_id: Optional[str] = None
    inputs: Dict[str, Any]
    predicted: Optional[Dict[str, Any]] = None
    actual: Optional[Dict[str, Any]] = None
    learning_signal: Optional[float] = None  # -1.0 to 1.0
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    jurisdiction: Jurisdiction = Jurisdiction.SANDBOX
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TaskOutcome(BaseModel):
    """
    Stores prediction and actual outcome for task-based learning.
    """
    outcome_id: UUID = Field(default_factory=uuid4)
    prediction_id: str
    api: APIType
    
    # Prediction data
    predicted_at: datetime
    inputs: Dict[str, Any]
    predicted: Dict[str, Any]
    confidence: Optional[float] = None
    
    # Actual outcome (filled later)
    actual: Optional[Dict[str, Any]] = None
    actual_at: Optional[datetime] = None
    outcome_delay_days: Optional[int] = None  # For delayed feedback
    
    # Learning
    learning_signal: Optional[float] = None
    processed: bool = False
    processed_at: Optional[datetime] = None


class KnowledgeItem(BaseModel):
    """
    Extracted knowledge from any learning domain.
    """
    knowledge_id: UUID = Field(default_factory=uuid4)
    domain: DomainType
    source: str  # URL, API call, or source identifier
    
    # Knowledge content
    fact: str
    entities: List[str] = Field(default_factory=list)
    relationships: List[Dict[str, str]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Credibility
    credibility_score: float = Field(ge=0.0, le=1.0)
    source_type: str  # "academic", "government", "commercial", etc.
    
    # Timestamps
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None


# ============================================================================
# CONSTITUTIONAL GOVERNANCE MODELS
# ============================================================================

class ConstitutionalValidation(BaseModel):
    """
    Result of constitutional governance validation.
    """
    validation_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Scoring
    benefit_score: float = Field(ge=0.0, le=100.0)
    harm_score: float = Field(ge=0.0, le=100.0)
    net_benefit: float  # benefit_score - harm_score
    
    # Decision
    decision: ConstitutionalDecision
    decision_reason: str
    
    # Detailed checks
    human_primacy_check: bool
    privacy_check: bool
    bias_check: bool
    sovereignty_check: bool
    
    # Violations (if any)
    violations: List[str] = Field(default_factory=list)
    
    # Override (for human review)
    human_override: Optional[bool] = None
    override_reason: Optional[str] = None
    override_by: Optional[str] = None


class AuditLogEntry(BaseModel):
    """
    Immutable audit trail entry for all constitutional decisions.
    """
    log_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Reference
    event_id: UUID
    validation_id: UUID
    
    # Decision details
    action_type: str
    decision: ConstitutionalDecision
    benefit_score: float
    harm_score: float
    
    # Context
    api: APIType
    domain: DomainType
    jurisdiction: Jurisdiction
    
    # Blockchain-style chaining
    previous_hash: Optional[str] = None
    current_hash: str
    
    class Config:
        frozen = True  # Immutable


# ============================================================================
# KNOWLEDGE GRAPH MODELS
# ============================================================================

class GraphNode(BaseModel):
    """
    Node in the knowledge graph.
    """
    node_id: UUID = Field(default_factory=uuid4)
    node_type: str  # "entity", "pattern", "fact", "concept"
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Learning metadata
    learned_from: DomainType
    learned_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(ge=0.0, le=1.0)


class GraphRelationship(BaseModel):
    """
    Relationship between nodes in the knowledge graph.
    """
    relationship_id: UUID = Field(default_factory=uuid4)
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: str  # "causes", "correlates_with", "part_of", etc.
    
    # Relationship strength
    strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence
    evidence_count: int = Field(ge=0)
    supporting_facts: List[UUID] = Field(default_factory=list)


class CrossDomainPattern(BaseModel):
    """
    Pattern that applies across multiple domains.
    """
    pattern_id: UUID = Field(default_factory=uuid4)
    pattern_name: str
    description: str
    
    # Domains where pattern appears
    source_domains: List[DomainType]
    applicable_apis: List[APIType]
    
    # Pattern structure
    pattern_structure: Dict[str, Any]
    generalization_rules: List[str]
    
    # Validation
    instances_observed: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)


# ============================================================================
# LEARNING METRICS MODELS
# ============================================================================

class LearningMetrics(BaseModel):
    """
    Metrics tracking for learning performance.
    """
    metric_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Scope
    domain: Optional[DomainType] = None
    api: Optional[APIType] = None
    timeframe_minutes: int = Field(ge=1)
    
    # Event counts
    total_events: int = Field(ge=0)
    processed_events: int = Field(ge=0)
    rejected_events: int = Field(ge=0)
    
    # Constitutional metrics
    approval_rate: float = Field(ge=0.0, le=1.0)
    avg_benefit_score: float = Field(ge=0.0, le=100.0)
    avg_harm_score: float = Field(ge=0.0, le=100.0)
    
    # Performance metrics
    avg_processing_time_ms: float = Field(ge=0.0)
    knowledge_items_added: int = Field(ge=0)
    patterns_discovered: int = Field(ge=0)


class ModelPerformance(BaseModel):
    """
    Tracks performance of specific models.
    """
    performance_id: UUID = Field(default_factory=uuid4)
    model_name: str
    model_version: str
    api: APIType
    
    # Performance metrics
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Business metrics
    predictions_made: int = Field(ge=0)
    outcomes_received: int = Field(ge=0)
    avg_learning_signal: Optional[float] = None
    
    # Timestamps
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_period_days: int = Field(ge=1)


# ============================================================================
# DOMAIN-SPECIFIC MODELS
# ============================================================================

class InternetSource(BaseModel):
    """
    Internet source for Domain 2 learning.
    """
    source_id: UUID = Field(default_factory=uuid4)
    url: str
    domain: str
    source_type: str  # "academic", "government", "news", etc.
    
    # Credibility
    credibility_score: float = Field(ge=0.0, le=1.0)
    citation_count: int = Field(ge=0, default=0)
    peer_reviewed: bool = False
    
    # Access
    last_crawled: Optional[datetime] = None
    crawl_frequency_hours: int = Field(ge=1, default=24)
    robots_compliant: bool = True


class UserInteraction(BaseModel):
    """
    User interaction event for Domain 3 learning.
    """
    interaction_id: UUID = Field(default_factory=uuid4)
    user_id: str
    api: APIType
    
    # Interaction details
    query: str
    response: str
    interaction_type: str  # "query", "feedback", "correction", etc.
    
    # Outcome
    user_satisfied: Optional[bool] = None
    explicit_feedback: Optional[str] = None
    implicit_signals: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamp
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityEvent(BaseModel):
    """
    Security event for Domain 7 learning.
    """
    security_id: UUID = Field(default_factory=uuid4)
    event_type: str  # "injection", "ddos", "abuse", "anomaly"
    severity: str  # "low", "medium", "high", "critical"
    
    # Event details
    source_ip: str
    user_id: Optional[str] = None
    request_pattern: Dict[str, Any]
    
    # Detection
    detected_by: str  # "sanitizer", "anomaly_detector", "rate_limiter"
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Response
    action_taken: str  # "blocked", "rate_limited", "flagged"
    blocked: bool
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ORCHESTRATOR MODELS
# ============================================================================

class LearningTask(BaseModel):
    """
    Task in the ILE orchestrator queue.
    """
    task_id: UUID = Field(default_factory=uuid4)
    event: LearningEvent
    priority: int = Field(ge=1, le=10, default=5)  # 1=lowest, 10=highest
    
    # Status
    status: str = Field(default="pending")  # pending, processing, completed, failed
    attempts: int = Field(ge=0, default=0)
    max_attempts: int = Field(ge=1, default=3)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_learning_signal(predicted: Dict[str, Any], actual: Dict[str, Any], 
                              api: APIType) -> float:
    """
    Calculate learning signal from prediction vs actual outcome.
    Returns value between -1.0 (very wrong) and 1.0 (very right).
    """
    # API-specific signal calculation
    if api == APIType.BUE:
        # For BUE: Compare predicted risk vs actual default
        predicted_risk = predicted.get("risk_score", 0.5)
        actual_default = actual.get("default", False)
        
        if actual_default:
            # Default happened: good prediction if high risk, bad if low risk
            return 2 * predicted_risk - 1  # Maps [0,1] to [-1,1]
        else:
            # No default: good prediction if low risk, bad if high risk
            return 1 - 2 * predicted_risk  # Maps [0,1] to [1,-1]
    
    # Default: simple accuracy-based signal
    return 1.0 if predicted == actual else -1.0
