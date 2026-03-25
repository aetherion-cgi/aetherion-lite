"""
Universal Intelligence Engine (UIE) Adapter
Handles reasoning, synthesis, and general intelligence queries
"""

import logging

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class UIEAdapter(BaseAdapter):
    """
    Adapter for the Universal Intelligence Engine.
    
    UIE is the middleware layer that can connect any LLM to Aetherion's capabilities.
    It handles general reasoning, planning, and synthesis tasks.
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke UIE with reasoning or synthesis request.
        
        UIE expects:
        {
            "tenant_id": str,
            "actor": str,
            "intent": dict,
            "payload": dict,
            "context": dict
        }
        """
        logger.info(f"Calling UIE for tenant={envelope.tenant_id}")
        
        try:
            # Build UIE request
            payload = {
                "tenant_id": envelope.tenant_id,
                "actor": envelope.actor,
                "intent": envelope.intent,
                "payload": envelope.payload,
                "context": envelope.context,
                "governance": envelope.governance.dict() if envelope.governance else None
            }
            
            # Call UIE
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            return NormalizedResult(
                data=sanitized.get("data") or sanitized.get("result"),
                details=sanitized.get("details"),
                governance=governance or envelope.governance,
                traces={
                    "uie_request_id": sanitized.get("request_id"),
                    "model_used": sanitized.get("model"),
                    "tokens_used": sanitized.get("tokens")
                }
            )
            
        except Exception as e:
            logger.exception("UIE adapter error")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "UIE_ERROR",
                    "message": "Intelligence engine error",
                    "category": "server",
                    "retryable": True
                },
                traces={"adapter": "UIEAdapter", "error": str(type(e).__name__)}
            )
