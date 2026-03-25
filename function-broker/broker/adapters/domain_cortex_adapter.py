"""
Domain Cortex Adapter
Handles meta-learning and cross-domain intelligence synthesis
"""

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter
import logging
logger = logging.getLogger(__name__)


class DomainCortexAdapter(BaseAdapter):
    """
    Adapter for the Domain Cortex.
    
    Domain Cortex provides:
    - Meta-learning across domains
    - Constitutional alignment learning
    - Cross-domain intelligence synthesis
    - Pattern recognition at system level
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke Domain Cortex with synthesis or meta-learning request.
        
        Domain Cortex expects:
        {
            "request_type": str,  # synthesis, meta_learning, pattern_analysis
            "domains": list[str],  # Domains to synthesize across
            "data": dict,  # Input data for analysis
            "tenant_id": str,
            "actor": str,
            "governance": dict
        }
        """
        logger.info(
            f"Calling Domain Cortex for tenant={envelope.tenant_id}, "
            f"request_type={envelope.payload.get('request_type')}, "
            f"domains={envelope.payload.get('domains')}"
        )
        
        try:
            # Build Domain Cortex request in the shape the local HTTP API actually expects.
            request_type = envelope.payload.get("request_type", "synthesis")
            domains = envelope.payload.get("domains", [])
            data = envelope.payload.get("data", envelope.payload)

            # Support both direct engine-style payloads (`text`) and UIE/public façade payloads (`prompt`).
            text_input = data.get("text")
            if not text_input:
                text_input = data.get("prompt", "")

            # Current local Domain Cortex endpoints accept a simple body:
            # {
            #   "text": str,
            #   "context": dict
            # }
            if request_type == "synthesis":
                payload = {
                    "text": text_input,
                    "context": {
                        "domains": domains,
                        "tenant_id": envelope.tenant_id,
                        "actor": envelope.actor,
                        "governance": envelope.governance.dict() if envelope.governance else None,
                        "request_context": envelope.context or {},
                    },
                }
            elif request_type == "meta_learning":
                payload = {
                    "samples": data.get("samples", []),
                    "parameters": {
                        **(data.get("parameters", {}) or {}),
                        "domains": domains,
                        "tenant_id": envelope.tenant_id,
                        "actor": envelope.actor,
                        "governance": envelope.governance.dict() if envelope.governance else None,
                        "request_context": envelope.context or {},
                    },
                }
            else:
                payload = {
                    "text": text_input or str(data),
                    "context": {
                        "request_type": request_type,
                        "domains": domains,
                        "tenant_id": envelope.tenant_id,
                        "actor": envelope.actor,
                        "governance": envelope.governance.dict() if envelope.governance else None,
                        "request_context": envelope.context or {},
                    },
                }

            logger.info(f"Domain Cortex endpoint: {self.descriptor.endpoint}")
            logger.info(f"Domain Cortex outbound payload: {payload}")

            # Call Domain Cortex
            response = await self._call_http_engine(payload, envelope)
            logger.info(f"RAW ENGINE RESPONSE: {response}")
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            logger.info(f"SANITIZED RESPONSE: {sanitized}")
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # Support both the richer future response shape and the current local service shape.
            synthesis_value = sanitized.get("synthesis") or sanitized.get("result")
            details_value = {
                "domain_contributions": sanitized.get("domain_contributions"),
                "cross_domain_patterns": sanitized.get("cross_domain_patterns"),
                "meta_learning_insights": sanitized.get("meta_learning_insights"),
                "constitutional_alignment": sanitized.get("constitutional_alignment"),
                "context_used": sanitized.get("context_used"),
                "status": sanitized.get("status"),
            }

            traces_value = {
                "cortex_request_id": sanitized.get("request_id"),
                "domains_analyzed": domains,
                "synthesis_time_ms": sanitized.get("synthesis_time_ms"),
                "endpoint": str(self.descriptor.endpoint),
            }

            return NormalizedResult(
                data={
                    "synthesis": synthesis_value,
                    "insights": sanitized.get("insights"),
                    "recommendations": sanitized.get("recommendations"),
                    "confidence": sanitized.get("confidence"),
                    "raw_status": sanitized.get("status"),
                },
                details=details_value,
                governance=governance or envelope.governance,
                traces=traces_value,
            )
            
        except Exception as e:
            logger.exception("DomainCortexAdapter failure")
            raise
