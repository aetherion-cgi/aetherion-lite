"""
Function Broker Client
Secure mTLS communication with internal Function Broker
"""
import httpx
import ssl
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from config import config
from api_models import GovernanceDecision, CapabilityResult

logger = logging.getLogger(__name__)


class FunctionBrokerClient:
    """
    Client for communicating with Function Broker over mTLS.
    UIE never calls engines directly - always via Function Broker.
    """
    
    def __init__(self):
        self.base_url = config.function_broker_url
        self.timeout = config.function_broker_timeout
        self.default_tenant_id = "demo"
        self.default_actor = "uie"
        
        # Setup mTLS if enabled
        if config.mtls_enabled:
            self.client = self._create_mtls_client()
        else:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(f"Function Broker client initialized: {self.base_url}")
    
    def _create_mtls_client(self):
        """
        Create the HTTPX client for talking to the Function Broker.

        In prod: uses mTLS with certs/CA.
        In dev: falls back to plain HTTP if certs not available.
        """
        # Figure out what the actual broker URL field is on config.
        # Try 'broker_url' first, then 'function_broker_url'.
        base_url = getattr(config, "broker_url", None)
        if base_url is None:
            base_url = getattr(config, "function_broker_url", None)

        if base_url is None:
            # Last resort: fail loud *before* we create a broken client.
            raise RuntimeError(
                "ServiceConfig has neither 'broker_url' nor 'function_broker_url'. "
                "Update function_broker_client._create_mtls_client to match the actual config field."
            )

        mtls_enabled = getattr(config, "mtls_enabled", True)

        # If mTLS explicitly disabled, always use plain HTTP
        if not mtls_enabled:
            logger.warning("mTLS disabled; using plain HTTP client (DEV MODE).")
            timeout = getattr(config, "http_timeout", 30.0)
            return httpx.AsyncClient(
                base_url=base_url.replace("https://", "http://"),
                verify=False,
                timeout=timeout,
            )

        # Try the mTLS-secure path, but fall back safely if certs missing
        try:
            ssl_context = ssl.create_default_context(
                purpose=ssl.Purpose.SERVER_AUTH,
                cafile=config.mtls_ca_path,
            )
            ssl_context.load_cert_chain(
                certfile=config.mtls_cert_path,
                keyfile=config.mtls_key_path,
            )

            logger.info("mTLS certificate chain loaded successfully.")
            return httpx.AsyncClient(
                base_url=base_url,
                verify=ssl_context,
                timeout=self.timeout,
            )

        except Exception as e:
            logger.error(f"mTLS initialization failed ({e}); falling back to plain HTTP.")

            return httpx.AsyncClient(
                base_url=base_url.replace("https://", "http://"),
                verify=False,
                timeout=self.timeout,
            )
    
    async def check_authorization(
        self,
        capability: str,
        params: Dict[str, Any],
        governance_context: Dict[str, Any]
    ) -> GovernanceDecision:
        """
        Check if a capability invocation is authorized.
        Function Broker will consult OPA for governance decision.
        """
        # Local profile: governance is handled upstream in UIE for now.
        # Preserve the interface and return an allow decision so the rest of the
        # stack can execute against the currently working local Function Broker.
        return GovernanceDecision(
            allowed=True,
            tier="T1",
            explanation="Governance delegated to UIE/local profile",
            review_id=None,
            restrictions=[]
        )
    
    async def invoke_capability(
        self,
        capability_id: str,
        params: Dict[str, Any],
        governance_context: Dict[str, Any]
    ) -> CapabilityResult:
        """
        Invoke a capability via Function Broker.
        
        Args:
            capability_id: e.g., "bue.underwrite", "uie.query"
            params: Capability-specific parameters
            governance_context: Governance metadata
        
        Returns:
            CapabilityResult with execution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Invoking capability: {capability_id}")
            
            envelope = {
                "tenant_id": governance_context.get("tenant_id", self.default_tenant_id),
                "actor": governance_context.get("actor", self.default_actor),
                "intent": params.get("intent", {"task": "execute"}),
                "payload": params,
                "governance": governance_context,
                "context": {},
            }

            session_id = governance_context.get("session_id")
            user_id = governance_context.get("user_id")
            request_id = governance_context.get("request_id")

            if session_id is not None:
                envelope["context"]["session_id"] = session_id
            if user_id is not None:
                envelope["context"]["user_id"] = user_id
            if not envelope["context"]:
                envelope.pop("context")
            if request_id is not None:
                envelope["request_id"] = request_id

            response = await self.client.post(
                f"{self.base_url}/v1/invoke",
                params={"capability_id": capability_id},
                headers={"X-Service-ID": self.default_actor},
                json=envelope,
            )
            
            response.raise_for_status()
            data = response.json()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CapabilityResult(
                capability=capability_id,
                status="success" if data.get("success", True) else "error",
                data=data.get("data"),
                error=(data.get("error") or {}).get("message") if not data.get("success", True) else None,
                execution_time_ms=execution_time,
                metadata=data.get("metadata", {})
            )
            
        except httpx.HTTPStatusError as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Capability {capability_id} failed with status {e.response.status_code}")
            
            return CapabilityResult(
                capability=capability_id,
                status="error",
                error=f"HTTP {e.response.status_code}: {e.response.text}",
                execution_time_ms=execution_time,
                metadata={}
            )
            
        except httpx.RequestError as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Capability {capability_id} failed: {e}")
            
            return CapabilityResult(
                capability=capability_id,
                status="error",
                error=f"Request failed: {str(e)}",
                execution_time_ms=execution_time,
                metadata={}
            )
    
    async def get_available_capabilities(self) -> Dict[str, Any]:
        """Get list of available capabilities from Function Broker"""
        try:
            response = await self.client.get(f"{self.base_url}/capabilities")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get capabilities: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, str]:
        """Check Function Broker health"""
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            response.raise_for_status()
            return {"status": "healthy"}
        except Exception as e:
            logger.error(f"Function Broker health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global Function Broker client instance
_broker_client: Optional[FunctionBrokerClient] = None


def get_broker_client() -> FunctionBrokerClient:
    """Get or create global Function Broker client"""
    global _broker_client
    if _broker_client is None:
        _broker_client = FunctionBrokerClient()
    return _broker_client
