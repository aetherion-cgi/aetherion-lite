"""
Universal Risk & Probabilistic Engine (URPE) Adapter
Handles strategic/military scenarios and existential risk assessment

CRITICAL: URPE is ONLY accessible via the Function Broker.
This adapter is the ONLY way to reach URPE - it is never directly exposed.
"""

import logging

from aetherion_common.schemas import Envelope, NormalizedResult, GovernanceMetadata
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class URPEAdapter(BaseAdapter):
    """
    Adapter for the Universal Risk & Probabilistic Engine.
    
    URPE handles 0.1% of critical military/strategic/existential scenarios.
    
    SECURITY CRITICAL:
    - URPE can ONLY be called via urpe.evaluate capability
    - Requires T3 governance tier (critical review)
    - Never directly exposed to external callers
    - All calls audited with constitutional compliance
    """

    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke URPE with strategic evaluation request.
        
        URPE expects:
        {
            "scenario": dict,  # Strategic/existential scenario
            "actor": str,
            "tenant_id": str,
            "governance": dict,
            "analysis_type": str  # military, geopolitical, existential, etc.
        }
        
        CRITICAL: This method adds additional security checks beyond
        the broker's standard validation.
        """
        scenario_type = envelope.payload.get("scenario_type")
        endpoint_str = str(self.descriptor.endpoint)
        is_evaluate = endpoint_str.endswith("/v1/evaluate")
        logger.warning(
            f"🚨 URPE invocation: tenant={envelope.tenant_id}, "
            f"actor={envelope.actor}, "
            f"scenario_type={scenario_type}"
        )
        
        try:
            # URPE-specific validation aligned to the live URPE API contract.
            if scenario_type not in [
                "military_strategic",
                "interplanetary",
                "existential_risk",
                "alien_intelligence",
                "deep_state_intelligence",
                "hybrid",
            ]:
                logger.error(f"Invalid URPE scenario type: {scenario_type}")
                return NormalizedResult(
                    data=None,
                    success=False,
                    error={
                        "code": "INVALID_ANALYSIS_TYPE",
                        "message": f"Invalid scenario type for URPE request: {scenario_type}",
                        "category": "client",
                        "retryable": False,
                    },
                )
            
            # Build URPE request in the shape the live URPE API actually expects.
            if is_evaluate:
                payload = {
                    "situation": envelope.payload.get("situation") or envelope.payload.get("scenario"),
                    "timeframe_years": envelope.payload.get("timeframe_years", 10),
                    "classification": envelope.payload.get("classification", "secret"),
                    "scenario_type": scenario_type,
                }
            else:
                payload = {
                    "scenario": envelope.payload.get("scenario") or envelope.payload.get("situation"),
                    "timeframe_years": envelope.payload.get("timeframe_years", 10),
                    "classification": envelope.payload.get("classification", "secret"),
                    "scenario_type": scenario_type,
                }

            if envelope.payload.get("context_data") is not None:
                payload["context_data"] = envelope.payload.get("context_data")
            
            # Call URPE with extended timeout (strategic analysis takes time)
            response = await self._call_http_engine(payload, envelope)
            
            # Sanitize response - URPE responses may contain sensitive strategic info
            sanitized = self._sanitize_engine_response(response)
            
            # CRITICAL: Remove any tactical details that shouldn't be exposed
            # Keep only strategic summaries and sanitized assessments
            if "tactical_details" in sanitized:
                del sanitized["tactical_details"]
            if "classified_sources" in sanitized:
                del sanitized["classified_sources"]

            # Normalize the live URPE API shape for broker consumers.
            if sanitized.get("constitutional_governance") is None:
                sanitized["constitutional_governance"] = {
                    "sovereignty_constraints": sanitized.get("sovereignty_constraints", []),
                    "ethical_constraints": sanitized.get("ethical_constraints", []),
                }
            
            # Extract governance if present
            governance = None
            if "governance" in sanitized:
                governance = GovernanceMetadata(**sanitized["governance"])
            
            # URPE returns strategic assessments with probabilistic outcomes
            return NormalizedResult(
                data={
                    "scenario_id": sanitized.get("scenario_id"),
                    "scenario_type": sanitized.get("scenario_type"),
                    "threat_level": sanitized.get("threat_level"),
                    "classification": sanitized.get("classification"),
                    "recommended_actions": sanitized.get("recommended_actions"),
                    "decision_tree": sanitized.get("decision_tree"),
                    "summary": sanitized.get("summary") or sanitized.get("assessment") or f"URPE {scenario_type} analysis complete",
                },
                details={
                    "governmental_review_required": sanitized.get("governmental_review_required"),
                    "human_primacy_validation": sanitized.get("human_primacy_validation"),
                    "commercial_feasibility": sanitized.get("commercial_feasibility") if sanitized.get("commercial_feasibility") is not None else sanitized.get("bue_analysis", {}).get("commercial_feasibility"),
                    "probabilistic_outcomes": sanitized.get("probabilistic_outcomes") or sanitized.get("bue_analysis", {}).get("probabilistic_outcomes"),
                    "risk_factors": sanitized.get("risk_factors") or sanitized.get("bue_analysis", {}).get("risk_factors"),
                    "modules_activated": sanitized.get("modules_activated"),
                    "constitutional_governance": sanitized.get("constitutional_governance"),
                    "timeline_projections": sanitized.get("timeline_projections") or sanitized.get("multi_decade_projections"),
                },
                governance=governance or envelope.governance,
                traces={
                    "urpe_request_id": sanitized.get("scenario_id") or sanitized.get("request_id"),
                    "scenario_type": scenario_type,
                    "execution_time_ms": sanitized.get("execution_time_ms"),
                    "constitutional_review": "required",
                    "endpoint": str(self.descriptor.endpoint),
                },
            )
            
        except Exception as e:
            logger.exception("URPE adapter error - strategic evaluation failed")
            return NormalizedResult(
                data=None,
                success=False,
                error={
                    "code": "URPE_ERROR",
                    "message": "Strategic evaluation error",
                    "category": "server",
                    "retryable": False,
                },
                traces={
                    "adapter": "URPEAdapter",
                    "error": str(type(e).__name__),
                    "exception_message": str(e),
                    "scenario_type": scenario_type,
                    "endpoint": endpoint_str,
                    "requires_investigation": True,
                },
            )
