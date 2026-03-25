"""
Internal Learning Engine (ILE) Adapter
Handles continuous constitutional learning across domains
"""

import logging

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class ILEAdapter(BaseAdapter):
    """
    Adapter for the Internal Learning Engine.
    
    ILE enables continuous learning across seven constitutional domains:
    1. Ethical reasoning
    2. Policy interpretation
    3. Risk assessment
    4. Cultural sensitivity
    5. Environmental impact
    6. Economic fairness
    7. Human-AI collaboration patterns
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke ILE with learning or feedback request.
        
        ILE expects:
        {
            "learning_type": str,  # feedback, pattern_analysis, policy_update
            "domain": str,  # Which constitutional domain
            "data": dict,  # Learning data or feedback
            "tenant_id": str,
            "actor": str,
            "governance": dict
        }
        """
        endpoint = str(self.descriptor.endpoint)
        is_feedback = endpoint.endswith("/v1/feedback")
        logger.info(
            f"Calling ILE for tenant={envelope.tenant_id}, "
            f"mode={'feedback' if is_feedback else 'learn'}, "
            f"domain={envelope.payload.get('domain')}"
        )
        
        try:
            # Build ILE request in the shape the live internal-only ILE API expects.
            if is_feedback:
                payload = {
                    "feedback": envelope.payload.get("feedback") or envelope.payload,
                    "domain": envelope.payload.get("domain", "user_interaction"),
                    "api": envelope.payload.get("api", envelope.actor or "uie"),
                    "metadata": envelope.payload.get("metadata") or {},
                }
            else:
                payload = {
                    "observation": envelope.payload.get("observation") or envelope.payload,
                    "domain": envelope.payload.get("domain", "task_based"),
                    "api": envelope.payload.get("api", envelope.actor or "bue"),
                    "metadata": envelope.payload.get("metadata") or {},
                }
            
            # Call ILE
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # ILE returns learning outcomes and updated patterns
            return NormalizedResult(
                data={
                    "status": sanitized.get("status"),
                    "queue_status": (sanitized.get("result") or {}).get("status"),
                    "task_id": (sanitized.get("result") or {}).get("task_id"),
                    "mode": (sanitized.get("result") or {}).get("mode"),
                    "message": (sanitized.get("result") or {}).get("message"),
                },
                details={
                    "domain": (sanitized.get("result") or {}).get("domain"),
                    "api": (sanitized.get("result") or {}).get("api"),
                    "raw_result": sanitized.get("result"),
                },
                governance=governance or envelope.governance,
                traces={
                    "ile_request_id": (sanitized.get("result") or {}).get("task_id") or sanitized.get("request_id"),
                    "endpoint": endpoint,
                    "operation": "feedback" if is_feedback else "learn",
                    "processing_time_ms": sanitized.get("processing_time_ms"),
                }
            )
            
        except Exception as e:
            logger.exception("ILE adapter error")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "ILE_ERROR",
                    "message": "Learning engine error",
                    "category": "server",
                    "retryable": True
                },
                traces={"adapter": "ILEAdapter", "error": str(type(e).__name__), "exception_message": str(e), "endpoint": endpoint}
            )
