"""
Compute Energy Orchestration API (CEOA) Adapter
Handles infrastructure optimization and workload scheduling
"""

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter


class CEOAAdapter(BaseAdapter):
    """
    Adapter for the Compute Energy Orchestration API.
    
    CEOA optimizes computational workload placement and energy consumption
    across distributed infrastructure.
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke CEOA with scheduling or optimization request.
        
        CEOA expects:
        {
            "workload": dict,  # Workload specification
            "tenant_id": str,
            "actor": str,
            "governance": dict,
            "constraints": dict  # Optional: resource constraints
        }
        """
        self.logger.info(
            f"Calling CEOA for tenant={envelope.tenant_id}, "
            f"description={envelope.payload.get('description')}"
        )
        
        try:
            # Build CEOA request in the shape the local CEOA API actually expects.
            payload = {
                "description": envelope.payload.get("description"),
                "docker_image": envelope.payload.get("docker_image"),
                "requirements": envelope.payload.get("requirements", {}),
            }

            # Optional passthrough fields for optimization-style routes.
            if "constraints" in envelope.payload:
                payload["constraints"] = envelope.payload["constraints"]
            if "workload_id" in envelope.payload:
                payload["workload_id"] = envelope.payload["workload_id"]
            if "tenant_id" in envelope.payload:
                payload["tenant_id"] = envelope.payload["tenant_id"]
            
            # Call CEOA
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # CEOA returns scheduling recommendations and resource allocations
            return NormalizedResult(
                data={
                    "workload_id": sanitized.get("id") or sanitized.get("workload_id"),
                    "status": sanitized.get("status"),
                    "placement": sanitized.get("placement"),
                    "optimization": sanitized.get("optimization"),
                    "schedule": sanitized.get("schedule"),
                    "primary": sanitized.get("primary"),
                    "alternatives": sanitized.get("alternatives"),
                    "reasoning": sanitized.get("reasoning"),
                },
                details={
                    "estimated_cost": sanitized.get("estimated_cost") or (sanitized.get("estimates") or {}).get("cost_usd"),
                    "estimated_energy": sanitized.get("estimated_energy") or (sanitized.get("estimates") or {}).get("carbon_kg"),
                    "estimated_duration_seconds": sanitized.get("estimated_duration_seconds") or (sanitized.get("estimates") or {}).get("duration_seconds"),
                    "optimization_metrics": sanitized.get("optimization_metrics"),
                    "alternative_schedules": sanitized.get("alternative_schedules"),
                    "resource_availability": sanitized.get("resource_availability"),
                    "carbon_impact": sanitized.get("carbon_impact"),
                },
                governance=governance or envelope.governance,
                traces={
                    "ceoa_request_id": sanitized.get("request_id") or sanitized.get("id"),
                    "scheduling_time_ms": sanitized.get("scheduling_time_ms"),
                    "nodes_evaluated": sanitized.get("nodes_evaluated"),
                    "endpoint": str(self.descriptor.endpoint),
                }
            )
            
        except Exception as e:
            self.logger.exception("CEOA adapter error")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "CEOA_ERROR",
                    "message": "Compute orchestration error",
                    "category": "server",
                    "retryable": True
                },
                traces={"adapter": "CEOAAdapter", "error": str(type(e).__name__)}
            )
