"""
Function Broker Metrics
Prometheus metrics collection for observability
"""

from typing import Dict, Optional
from dataclasses import dataclass, asdict
import time

from broker.core.models import InvocationMetrics
from broker.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricsSummary:
    """Summary statistics for metrics reporting"""
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    average_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0


class MetricsCollector:
    """
    Collects and exports metrics for the Function Broker.
    
    In production, this integrates with Prometheus for monitoring.
    """
    
    def __init__(self):
        self._invocations: list[InvocationMetrics] = []
        self._capability_metrics: Dict[str, MetricsSummary] = {}
        self._tenant_metrics: Dict[str, MetricsSummary] = {}
        
    def record_invocation(self, metrics: InvocationMetrics) -> None:
        """Record metrics for a capability invocation"""
        self._invocations.append(metrics)
        
        # Update capability-specific metrics
        if metrics.capability_id not in self._capability_metrics:
            self._capability_metrics[metrics.capability_id] = MetricsSummary()
        
        cap_metrics = self._capability_metrics[metrics.capability_id]
        cap_metrics.total_invocations += 1
        
        if metrics.success:
            cap_metrics.successful_invocations += 1
        else:
            cap_metrics.failed_invocations += 1
        
        # Update tenant-specific metrics
        if metrics.tenant_id not in self._tenant_metrics:
            self._tenant_metrics[metrics.tenant_id] = MetricsSummary()
        
        tenant_metrics = self._tenant_metrics[metrics.tenant_id]
        tenant_metrics.total_invocations += 1
        
        if metrics.success:
            tenant_metrics.successful_invocations += 1
        else:
            tenant_metrics.failed_invocations += 1
        
        logger.debug(
            f"Recorded metrics: {metrics.capability_id} "
            f"success={metrics.success} duration={metrics.duration_ms}ms"
        )
    
    def get_capability_metrics(self, capability_id: str) -> Optional[MetricsSummary]:
        """Get metrics summary for a specific capability"""
        return self._capability_metrics.get(capability_id)
    
    def get_tenant_metrics(self, tenant_id: str) -> Optional[MetricsSummary]:
        """Get metrics summary for a specific tenant"""
        return self._tenant_metrics.get(tenant_id)
    
    def get_all_metrics(self) -> dict:
        """Get all collected metrics"""
        return {
            "total_invocations": len(self._invocations),
            "capabilities": {
                cap_id: asdict(metrics)
                for cap_id, metrics in self._capability_metrics.items()
            },
            "tenants": {
                tenant_id: asdict(metrics)
                for tenant_id, metrics in self._tenant_metrics.items()
            }
        }
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        In production, this would be exposed at /metrics endpoint.
        """
        lines = [
            "# HELP broker_invocations_total Total number of capability invocations",
            "# TYPE broker_invocations_total counter"
        ]
        
        for cap_id, metrics in self._capability_metrics.items():
            lines.append(
                f'broker_invocations_total{{capability="{cap_id}",status="success"}} '
                f'{metrics.successful_invocations}'
            )
            lines.append(
                f'broker_invocations_total{{capability="{cap_id}",status="error"}} '
                f'{metrics.failed_invocations}'
            )
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing)"""
        self._invocations.clear()
        self._capability_metrics.clear()
        self._tenant_metrics.clear()
        logger.info("Metrics reset")
