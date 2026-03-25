"""
Business Underwriting Engine (BUE) Adapter
Handles commercial risk analytics and underwriting
"""

import logging

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class BUEAdapter(BaseAdapter):
    """
    Adapter for the Business Underwriting Engine.
    
    BUE handles 99.9% of planetary-scale commercial operations through
    sophisticated Monte Carlo simulations and multi-signal intelligence.
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke BUE with underwriting request.
        
        BUE expects:
        {
            "scenario": dict,  # The underwriting scenario
            "actor": str,
            "tenant_id": str,
            "governance": dict,
            "signals": list[str]  # Optional: specific signals to use
        }
        """
        endpoint = str(self.descriptor.endpoint)
        is_underwrite = endpoint.endswith("/api/v1/underwrite")
        logger.info(
            f"Calling BUE for tenant={envelope.tenant_id}, "
            f"mode={'underwrite' if is_underwrite else 'analyze'}, "
            f"asset_type={envelope.payload.get('asset_type')}"
        )
        
        try:
            # Build BUE request in the shape the live BUE REST wrapper expects.
            if is_underwrite:
                payload = {
                    "project": envelope.payload.get("project") or envelope.payload.get("scenario") or "Underwriting request",
                    "capex": envelope.payload.get("capex", 0),
                    "expected_revenue": envelope.payload.get("expected_revenue", 0),
                    "asset_type": envelope.payload.get("asset_type", "cre"),
                }
            else:
                payload = {
                    "scenario": envelope.payload.get("scenario") or envelope.payload.get("project") or "Scenario analysis request",
                    "asset_type": envelope.payload.get("asset_type", "cre"),
                }

            if envelope.payload.get("metadata") is not None:
                payload["metadata"] = envelope.payload.get("metadata")
            
            # Call BUE
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # BUE returns comprehensive underwriting results
            return NormalizedResult(
                data={
                    "id": sanitized.get("id"),
                    "score": sanitized.get("score"),
                    "rating": sanitized.get("rating"),
                    "summary": sanitized.get("summary") or f"BUE {'underwrite' if is_underwrite else 'analyze'} completed",
                    "recommendation": sanitized.get("recommendation"),
                },
                details={
                    "timestamp": sanitized.get("timestamp"),
                    "execution_time_ms": sanitized.get("execution_time_ms"),
                    "metrics": sanitized.get("metrics"),
                    "risk_analysis": sanitized.get("risk_analysis"),
                    "forecast": sanitized.get("forecast"),
                    "governance": sanitized.get("governance"),
                },
                governance=governance or envelope.governance,
                traces={
                    "bue_request_id": sanitized.get("id") or sanitized.get("request_id"),
                    "endpoint": endpoint,
                    "operation": "underwrite" if is_underwrite else "analyze",
                    "asset_type": payload.get("asset_type"),
                    "execution_time_ms": sanitized.get("execution_time_ms"),
                }
            )
            
        except Exception as e:
            logger.exception("BUE adapter error")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "BUE_ERROR",
                    "message": "Underwriting engine error",
                    "category": "server",
                    "retryable": True
                },
                traces={"adapter": "BUEAdapter", "error": str(type(e).__name__), "exception_message": str(e), "endpoint": endpoint}
            )
