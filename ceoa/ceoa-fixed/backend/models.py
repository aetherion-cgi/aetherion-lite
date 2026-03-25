"""
Database models for CEOA.

Strategy: Use Postgres with JSON/JSONB columns for v1 topology storage instead of Neo4j.
This reduces operational complexity while maintaining query flexibility.
Can migrate to Neo4j later if graph traversal becomes performance bottleneck.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base model for all database tables"""
    pass


# ============================================================================
# ENUMS
# ============================================================================
class WorkloadStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderType(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    DEVICE_MESH = "device_mesh"
    ON_PREMISE = "on_premise"


class InfrastructureType(str, enum.Enum):
    CLOUD = "cloud"
    DATACENTER = "datacenter"
    DEVICE_MESH = "device_mesh"
    EDGE = "edge"


class DeviceStatus(str, enum.Enum):
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"


class GovernanceTier(str, enum.Enum):
    ROUTINE = "routine"
    ELEVATED = "elevated"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"


# ============================================================================
# WORKLOAD MODELS
# ============================================================================
class Workload(Base):
    """Workload submission and execution tracking"""
    __tablename__ = "workloads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Workload definition
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docker_image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Requirements and preferences (stored as JSONB for flexibility)
    requirements: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default={})
    data_sources: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=[])
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default={})
    
    # Status and lifecycle
    status: Mapped[WorkloadStatus] = mapped_column(
        Enum(WorkloadStatus), nullable=False, default=WorkloadStatus.PENDING, index=True
    )
    
    # Placement (nullable until scheduled)
    placement: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Estimates (calculated during placement optimization)
    estimates: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Actuals (populated during/after execution)
    actuals: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Governance
    governance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    executions: Mapped[List["WorkloadExecution"]] = relationship(back_populates="workload")


# Create index on JSONB fields for common queries
Index(
    'idx_workload_requirements_cpu',
    Workload.requirements['cpu_cores'].cast(Float)
)


class WorkloadExecution(Base):
    """Track individual execution attempts (retries, migrations)"""
    __tablename__ = "workload_executions"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workload_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workloads.id"), nullable=False, index=True
    )
    
    # Execution details
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Metrics
    actual_duration_seconds: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    actual_cost_usd: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    actual_carbon_kg: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    actual_energy_kwh: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    
    # Status
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    workload: Mapped["Workload"] = relationship(back_populates="executions")


# ============================================================================
# INFRASTRUCTURE MODELS (Postgres-based topology, not Neo4j)
# ============================================================================
class InfrastructureNode(Base):
    """
    Infrastructure nodes with JSON-based topology relationships.
    
    Strategy: Store relationships as JSON arrays instead of graph edges.
    For v1, most queries are simple lookups (find nodes in region X with GPU Y).
    If we need complex graph traversal later, we can migrate to Neo4j without
    changing the API layer (interface stays abstract).
    """
    __tablename__ = "infrastructure_nodes"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[InfrastructureType] = mapped_column(
        Enum(InfrastructureType), nullable=False, index=True
    )
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False, index=True)
    
    # Location
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Capabilities (JSONB for flexibility)
    capabilities: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Availability
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    available_cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    available_memory_gb: Mapped[Float] = mapped_column(Float, nullable=False)
    queue_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Pricing
    pricing: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Topology relationships (stored as JSON arrays instead of graph edges)
    # This avoids Neo4j complexity for v1 while keeping the data accessible
    connected_nodes: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=[])
    data_sources: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=[])
    
    # Metrics (updated periodically)
    current_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default={})
    
    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_metrics_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# Create GIN index for JSONB queries
Index('idx_node_capabilities', InfrastructureNode.capabilities, postgresql_using='gin')


# ============================================================================
# DEVICE MESH MODELS
# ============================================================================
class Device(Base):
    """Device mesh participants (phones, laptops, IoT devices)"""
    __tablename__ = "devices"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Device information
    device_info: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Participation preferences
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Status
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), nullable=False, default=DeviceStatus.IDLE, index=True
    )
    
    # Earnings
    total_earned_usd: Mapped[Float] = mapped_column(Float, nullable=False, default=0.0)
    pending_earned_usd: Mapped[Float] = mapped_column(Float, nullable=False, default=0.0)
    paid_earned_usd: Mapped[Float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Statistics
    workloads_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compute_hours_contributed: Mapped[Float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# ============================================================================
# ENERGY & CARBON MODELS
# ============================================================================
class CarbonIntensityCache(Base):
    """Cache for carbon intensity data (EMA forecasting)"""
    __tablename__ = "carbon_intensity_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Current intensity
    carbon_intensity_gco2_kwh: Mapped[Float] = mapped_column(Float, nullable=False)
    
    # Source and confidence
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[Float] = mapped_column(Float, nullable=False, default=1.0)
    
    # Forecasting metadata
    is_forecast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forecast_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Cached at
    cached_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# Unique index to prevent duplicate cache entries
Index('idx_carbon_cache_unique', CarbonIntensityCache.region, CarbonIntensityCache.timestamp, unique=True)


class CarbonFootprint(Base):
    """Carbon footprint tracking per tenant"""
    __tablename__ = "carbon_footprints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Period
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Totals
    total_carbon_kg: Mapped[Float] = mapped_column(Float, nullable=False)
    total_energy_kwh: Mapped[Float] = mapped_column(Float, nullable=False)
    total_cost_usd: Mapped[Float] = mapped_column(Float, nullable=False)
    
    # Baseline (without CEOA optimization)
    baseline_carbon_kg: Mapped[Float] = mapped_column(Float, nullable=False)
    baseline_cost_usd: Mapped[Float] = mapped_column(Float, nullable=False)
    
    # Savings
    carbon_saved_kg: Mapped[Float] = mapped_column(Float, nullable=False)
    cost_saved_usd: Mapped[Float] = mapped_column(Float, nullable=False)
    
    # Breakdown by region/provider
    breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default={})
    
    # Calculated at
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# ============================================================================
# GOVERNANCE MODELS
# ============================================================================
class GovernanceAudit(Base):
    """Immutable audit trail for governance decisions"""
    __tablename__ = "governance_audits"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workload_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workloads.id"), nullable=False, index=True
    )
    
    # Evaluation results
    authorized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tier: Mapped[GovernanceTier] = mapped_column(Enum(GovernanceTier), nullable=False)
    benefit_score: Mapped[Float] = mapped_column(Float, nullable=False)
    harm_score: Mapped[Float] = mapped_column(Float, nullable=False)
    sovereignty_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # Violations
    violations: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=[])
    
    # Policy bundle used
    policy_bundle_version: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # OPA decision
    opa_decision: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Timestamp (immutable)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# ============================================================================
# SCHEDULER METRICS (for learning and optimization)
# ============================================================================
class PlacementDecision(Base):
    """Track placement decisions for learning/optimization"""
    __tablename__ = "placement_decisions"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workload_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workloads.id"), nullable=False, index=True
    )
    
    # Features used for placement
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Placement scores for alternatives
    alternatives: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    
    # Selected placement
    selected_placement: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    placement_score: Mapped[Float] = mapped_column(Float, nullable=False)
    
    # Reasoning (AI-generated)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Actual outcomes (for feedback loop)
    actual_cost_usd: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    actual_carbon_kg: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    actual_duration_seconds: Mapped[Optional[Float]] = mapped_column(Float, nullable=True)
    
    # Was this placement optimal? (for training data)
    was_optimal: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Timestamp
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
