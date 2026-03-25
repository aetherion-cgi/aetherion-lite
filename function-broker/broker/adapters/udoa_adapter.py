"""
Universal Data Orchestration API (UDOA) Adapter
Handles governed data access and platform integration
"""

import logging

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class UDOAAdapter(BaseAdapter):
    """
    Adapter for the Universal Data Orchestration API.
    
    UDOA provides governed access to enterprise data platforms while maintaining
    constitutional compliance and PII protection.
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke UDOA with data query or orchestration request.
        
        UDOA expects:
        {
            "query": dict,  # The data query specification
            "tenant_id": str,
            "actor": str,
            "governance": dict,
            "sources": list[str]  # Optional: specific data sources
        }
        """
        endpoint = str(self.descriptor.endpoint)
        is_aggregate = endpoint.endswith("/v1/aggregate")
        logger.info(
            f"Calling UDOA for tenant={envelope.tenant_id}, "
            f"mode={'aggregate' if is_aggregate else 'query'}, "
            f"query={envelope.payload.get('query')}, "
            f"metric={envelope.payload.get('metric')}"
        )
        
        try:
            # Build UDOA request in the shape the live UDOA API expects.
            if is_aggregate:
                payload = {
                    "sources": envelope.payload.get("sources") or [],
                    "metric": envelope.payload.get("metric") or "aggregate_request",
                }
                if envelope.payload.get("filters") is not None:
                    payload["filters"] = envelope.payload.get("filters")
            else:
                payload = {
                    "query": envelope.payload.get("query") or "data query",
                }
                if envelope.payload.get("context") is not None:
                    payload["context"] = envelope.payload.get("context")
            
            # Call UDOA
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response
            sanitized = self._sanitize_engine_response(response)
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # UDOA returns data with provenance and quality metrics
            return NormalizedResult(
                data={
                    "query": sanitized.get("query"),
                    "metric": sanitized.get("metric"),
                    "mode": sanitized.get("mode"),
                    "results": sanitized.get("results"),
                    "aggregate": sanitized.get("aggregate"),
                    "summary": (
                        ((sanitized.get("aggregate") or {}).get("summary"))
                        or (((sanitized.get("results") or [{}])[0]).get("summary") if sanitized.get("results") else None)
                    ),
                },
                details={
                    "sources": sanitized.get("sources"),
                    "source_count": (sanitized.get("aggregate") or {}).get("source_count"),
                    "filters": (sanitized.get("aggregate") or {}).get("filters"),
                    "raw_response": sanitized,
                },
                governance=governance or envelope.governance,
                traces={
                    "udoa_request_id": sanitized.get("request_id") or sanitized.get("metric") or sanitized.get("query"),
                    "endpoint": endpoint,
                    "operation": "aggregate" if is_aggregate else "query",
                    "mode": sanitized.get("mode"),
                }
            )
            
        except Exception as e:
            logger.exception("UDOA adapter error")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "UDOA_ERROR",
                    "message": "Data orchestration error",
                    "category": "server",
                    "retryable": True
                },
                traces={"adapter": "UDOAAdapter", "error": str(type(e).__name__), "exception_message": str(e), "endpoint": endpoint}
            )
