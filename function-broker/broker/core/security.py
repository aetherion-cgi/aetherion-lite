"""
Function Broker Security
Authentication, authorization, and governance constraint checking
"""

from typing import Optional
from fastapi import HTTPException, status, Request
from aetherion_common.schemas import Envelope, GovernanceMetadata
from aetherion_common.enums import GovernanceTier

from .models import CapabilityDescriptor
from ..observability.logging import get_logger

logger = get_logger(__name__)


class SecurityError(Exception):
    """Base exception for security violations"""
    pass


class AuthenticationError(SecurityError):
    """Authentication failed"""
    pass


class AuthorizationError(SecurityError):
    """Authorization failed"""
    pass


class GovernanceViolation(SecurityError):
    """Governance constraints violated"""
    pass


class BrokerSecurity:
    """
    Security enforcement for the Function Broker.
    
    Critical rules:
    1. Only internal services can call the broker
    2. Tenants can only access their own data
    3. Governance constraints must be satisfied
    4. URPE can only be accessed via urpe.evaluate capability
    """

    def __init__(self, internal_network_cidrs: list[str], strict_mode: bool = True):
        self.internal_network_cidrs = internal_network_cidrs
        self.strict_mode = strict_mode
        self._internal_service_tokens = set()  # In production, use proper token validation

    def check_internal_call(self, request: Optional[Request] = None) -> None:
        """
        Verify request comes from internal service mesh.
        
        In production:
        - Check mTLS client certificate
        - Verify service mesh headers
        - Validate JWT tokens
        """
        if not self.strict_mode:
            return
        
        # In production: implement proper mTLS verification
        # For now: check if request has internal service headers
        if request:
            service_id = request.headers.get("X-Service-ID")
            if not service_id:
                logger.warning("Request missing X-Service-ID header")
                raise AuthenticationError("Missing service authentication")
            
            if not self._is_internal_service(service_id):
                logger.error(f"Unauthorized service: {service_id}")
                raise AuthenticationError("Service not authorized")

    def _is_internal_service(self, service_id: str) -> bool:
        """Check if service ID is authorized to call broker"""
        # In production: check against service registry
        allowed_services = {
            "cortex-gateway",
            "uie",
            "domain-cortex",
            "domain_cortex",
            "cortex",
            "function-broker",
            "function_broker",
            "broker",
            "bue",
            "urpe",
            "ceoa",
            "udoa",
            "system",
            "admin-api",
            "ile"
        }
        return service_id in allowed_services

    def check_tenant_actor(self, envelope: Envelope) -> None:
        """
        Verify tenant and actor are valid and authorized.
        
        In production:
        - Validate tenant exists and is active
        - Verify actor has permission for tenant
        - Check actor authentication status
        """
        if not envelope.tenant_id:
            raise AuthorizationError("Missing tenant_id")
        
        if not envelope.actor:
            raise AuthorizationError("Missing actor")
        
        # In production: validate against tenant database
        logger.debug(f"Validated tenant={envelope.tenant_id}, actor={envelope.actor}")

    def check_governance_constraints(
        self,
        descriptor: CapabilityDescriptor,
        governance: GovernanceMetadata
    ) -> None:
        """
        Verify governance metadata meets capability requirements.
        
        Critical: This enforces constitutional governance constraints.
        """
        # If requested tier is HALT, immediately reject
        if governance.requested_tier == GovernanceTier.HALT:
            logger.error("Request with HALT tier rejected")
            raise GovernanceViolation("Operation halted by governance policy")
        
        # Verify tier is appropriate for capability
        capability_tier = descriptor.default_governance_tier
        requested_tier = governance.requested_tier
        
        if requested_tier != GovernanceTier.AUTO:
            # If explicitly requesting lower tier than default, reject
            tier_hierarchy = {"T1": 3, "T2": 2, "T3": 1, "halt": 0}
            
            if tier_hierarchy.get(requested_tier.value, 0) < tier_hierarchy.get(capability_tier, 0):
                logger.warning(
                    f"Requested tier {requested_tier} below capability requirement {capability_tier}"
                )
                raise GovernanceViolation(
                    f"Capability requires minimum tier {capability_tier}"
                )
        
        # CRITICAL: URPE access control
        if descriptor.id == "urpe.evaluate":
            # URPE can only be called via Function Broker, never directly
            # Additional checks for strategic/existential scenarios
            if "strategy" not in descriptor.domains and "governance" not in descriptor.domains:
                logger.error("Invalid URPE access attempt")
                raise GovernanceViolation("URPE access requires strategic context")
            
            # URPE always requires at least T3 (critical review)
            if requested_tier != GovernanceTier.AUTO and requested_tier.value not in ["T3"]:
                logger.warning(f"URPE access with insufficient tier: {requested_tier}")
                raise GovernanceViolation("URPE requires T3 governance tier")

    def check_capability_allowed(
        self,
        capability_id: str,
        tenant_id: str,
        actor: str
    ) -> None:
        """
        Check if actor is allowed to invoke this capability for this tenant.
        
        In production:
        - Check role-based access control (RBAC)
        - Verify capability quotas/rate limits
        - Check feature flags
        """
        # In production: implement RBAC check
        logger.debug(
            f"Capability access check: {capability_id} "
            f"by {actor} for tenant {tenant_id}"
        )

    def sanitize_error(self, error: Exception) -> dict:
        """
        Sanitize error for external consumption.
        CRITICAL: Never expose internal details, stack traces, or policy logic.
        """
        if isinstance(error, (AuthenticationError, AuthorizationError, GovernanceViolation)):
            return {
                "code": type(error).__name__.upper(),
                "message": str(error),
                "category": "governance" if isinstance(error, GovernanceViolation) else "client"
            }
        
        # For unexpected errors, return generic message
        logger.exception("Unexpected error occurred")
        return {
            "code": "INTERNAL_ERROR",
            "message": "An error occurred during processing",
            "category": "server"
        }

    def validate_escalation(
        self,
        governance: GovernanceMetadata,
        descriptor: CapabilityDescriptor
    ) -> None:
        """
        Validate escalation target if specified.
        
        Escalation rules:
        - BUE can escalate to URPE for strategic scenarios
        - UDOA can escalate to Domain Cortex for complex queries
        - URPE cannot escalate (it's the final authority)
        """
        if not governance.escalation_target:
            return
        
        target = governance.escalation_target.value
        
        # URPE cannot escalate
        if descriptor.id == "urpe.evaluate":
            raise GovernanceViolation("URPE cannot escalate")
        
        # Validate escalation path
        valid_escalations = {
            "bue.underwrite": ["URPE"],
            "udoa.query": ["DOMAIN_CORTEX"],
            "uie.query": ["DOMAIN_CORTEX", "URPE"]
        }
        
        allowed_targets = valid_escalations.get(descriptor.id, [])
        if target not in allowed_targets:
            raise GovernanceViolation(
                f"Invalid escalation: {descriptor.id} cannot escalate to {target}"
            )
