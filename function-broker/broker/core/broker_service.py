"""
Function Broker Service
Core orchestration logic for capability invocation
"""

import time
from typing import Optional
from fastapi import Request

from aetherion_common.schemas import Envelope, NormalizedResult, ErrorDetail
from aetherion_common.enums import GovernanceTier

from .models import CapabilityDescriptor, InvocationMetrics
from .registry import CapabilityRegistry
from .security import BrokerSecurity, SecurityError
from ..observability.logging import get_logger
from ..observability.metrics import MetricsCollector

logger = get_logger(__name__)


class FunctionBrokerService:
    """
    Core service for Function Broker.
    
    Responsibilities:
    1. Validate security and governance
    2. Look up capability and build adapter
    3. Invoke adapter with envelope
    4. Return sanitized NormalizedResult
    5. Emit metrics and audit logs
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        security: BrokerSecurity,
        metrics: MetricsCollector
    ):
        self.registry = registry
        self.security = security
        self.metrics = metrics

    async def invoke(
        self,
        capability_id: str,
        envelope: Envelope,
        request: Optional[Request] = None
    ) -> NormalizedResult:
       
        """
        Invoke a capability with the given envelope.
        
        This is the main entry point for all capability invocations.
        """
        start_time = time.time()
        
        metrics_data = InvocationMetrics(
            capability_id=capability_id,
            request_id=envelope.request_id,
            tenant_id=envelope.tenant_id,
            actor=envelope.actor,
            start_time=start_time,
            governance_tier=envelope.governance.requested_tier.value
        )
        
        try:
            # 1. Security checks
            logger.info(
                f"Invoking capability {capability_id} "
                f"for tenant={envelope.tenant_id}, actor={envelope.actor}"
            )
            
            self.security.check_internal_call(request)
            self.security.check_tenant_actor(envelope)
            
            # 2. Get capability descriptor
            descriptor = self.registry.get(capability_id)
            
            # 3. Governance checks
            self.security.check_governance_constraints(descriptor, envelope.governance)
            self.security.validate_escalation(envelope.governance, descriptor)
            self.security.check_capability_allowed(
                capability_id,
                envelope.tenant_id,
                envelope.actor
            )
            
            # 4. Build adapter
            adapter = self.registry.build_adapter(descriptor)
            
            # 5. Invoke adapter
            logger.debug(f"Calling adapter for {capability_id}")
            result = await adapter.call(envelope)
            
            # 6. Enrich result with traces
            result.traces = result.traces or {}
            result.traces["capability_id"] = capability_id
            result.traces["broker_request_id"] = envelope.request_id
            result.traces["governance_tier"] = envelope.governance.requested_tier.value
            
            # 7. Update metrics
            end_time = time.time()
            metrics_data.end_time = end_time
            metrics_data.duration_ms = (end_time - start_time) * 1000
            metrics_data.success = result.success
            
            if result.governance:
                metrics_data.benefit_score = result.governance.benefit_score
                metrics_data.harm_score = result.governance.harm_score
            
            self.metrics.record_invocation(metrics_data)
            
            logger.info(
                f"Successfully invoked {capability_id} "
                f"in {metrics_data.duration_ms:.2f}ms"
            )
            
            return result
            
        except SecurityError as e:
            # Security violations are logged but returned as clean errors
            logger.warning(f"Security error for {capability_id}: {e}")
            metrics_data.success = False
            metrics_data.error_code = type(e).__name__
            self.metrics.record_invocation(metrics_data)
            
            error_detail = ErrorDetail(
                code=type(e).__name__.upper(),
                message=str(e),
                category="governance" if "Governance" in type(e).__name__ else "client",
                retryable=False
            )
            
            return NormalizedResult(
                data=None,
                success=False,
                error=error_detail,
                traces={
                    "capability_id": capability_id,
                    "error_type": type(e).__name__
                }
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    async def list_capabilities(
        self,
        tenant_id: str,
        actor: str,
        domain: Optional[str] = None
    ) -> list[dict]:
        """
        List available capabilities for a tenant/actor.
        
        Returns sanitized capability information (no internal details).
        """
        capabilities = self.registry.list_capabilities(domain=domain)
        
        # Sanitize capability information
        sanitized = []
        for cap in capabilities:
            sanitized.append({
                "id": cap.id,
                "display_name": cap.display_name,
                "description": cap.description,
                "domains": cap.domains,
                "default_governance_tier": cap.default_governance_tier,
                "tags": cap.tags
            })
        
        logger.info(
            f"Listed {len(sanitized)} capabilities for tenant={tenant_id}, domain={domain}"
        )
        
        return sanitized

    async def health_check(self) -> dict:
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "function-broker",
            "capabilities_count": len(self.registry._capabilities)
        }
