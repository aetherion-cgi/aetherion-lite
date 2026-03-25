"""
Function Broker Core Models
Capability descriptors and metadata for the function registry
"""

from pydantic import BaseModel, AnyUrl, Field
from enum import Enum
from typing import Dict, List, Optional, Literal, Any


class AdapterType(str, Enum):
    """Communication protocol for engine adapters"""
    HTTP = "http"
    KAFKA = "kafka"
    GRPC = "grpc"


class CapabilityDescriptor(BaseModel):
    """
    Metadata describing a capability and how to invoke it.
    Each capability maps to one internal engine via an adapter.
    """
    id: str = Field(
        ...,
        description="Unique capability identifier (e.g., 'bue.underwrite')"
    )
    display_name: str = Field(
        ...,
        description="Human-readable capability name"
    )
    description: str = Field(
        ...,
        description="What this capability does"
    )
    adapter: str = Field(
        ...,
        description="Adapter class name (e.g., 'BUEAdapter')"
    )
    adapter_type: AdapterType = Field(
        ...,
        description="Communication protocol"
    )
    endpoint: Optional[AnyUrl] = Field(
        default=None,
        description="HTTP/gRPC endpoint for the engine"
    )
    topic: Optional[str] = Field(
        default=None,
        description="Kafka topic for event-based engines"
    )
    default_governance_tier: Literal["T1", "T2", "T3", "halt"] = Field(
        default="T2",
        description="Default authorization tier if not specified"
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Domain classifications for routing"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata tags"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    retry_policy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_attempts": 3,
            "backoff_multiplier": 2,
            "initial_delay_ms": 100
        },
        description="Retry configuration"
    )
    requires_mtls: bool = Field(
        default=True,
        description="Whether this capability requires mTLS"
    )

    class Config:
        use_enum_values = True


class AdapterConfig(BaseModel):
    """Configuration for adapter instances"""
    ca_bundle: Optional[str] = Field(
        default="/etc/ssl/certs/aetherion-ca.crt",
        description="Path to CA bundle for mTLS"
    )
    client_cert: Optional[str] = Field(
        default="/etc/ssl/certs/function-broker.crt",
        description="Path to client certificate"
    )
    client_key: Optional[str] = Field(
        default="/etc/ssl/private/function-broker.key",
        description="Path to client private key"
    )
    default_timeout: int = Field(
        default=30,
        description="Default timeout for adapter calls"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts"
    )


class InvocationMetrics(BaseModel):
    """Metrics for capability invocation"""
    capability_id: str
    request_id: str
    tenant_id: str
    actor: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_code: Optional[str] = None
    governance_tier: Optional[str] = None
    benefit_score: Optional[float] = None
    harm_score: Optional[float] = None
