"""
Base Adapter Class
Abstract interface for all engine adapters
"""

from abc import ABC, abstractmethod
from typing import Optional
import httpx

from aetherion_common.schemas import Envelope, NormalizedResult
from broker.core.models import CapabilityDescriptor, AdapterConfig
from broker.observability.logging import get_logger

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """
    Abstract base class for all engine adapters.
    
    Adapters are responsible for:
    1. Translating Envelope to engine-specific request format
    2. Calling the engine (via HTTP, Kafka, etc.)
    3. Translating engine response to NormalizedResult
    4. Sanitizing any errors (never expose internals)
    """

    def __init__(self, descriptor: CapabilityDescriptor, settings: AdapterConfig):
        self.descriptor = descriptor
        self.settings = settings
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def call(self, envelope: Envelope) -> NormalizedResult:
        """
        Invoke the engine with the given envelope.
        
        Implementation must:
        - Build engine-specific request
        - Handle errors gracefully
        - Return sanitized NormalizedResult
        - NEVER expose internal engine details
        """
        pass

    def _create_http_client(self, timeout: Optional[int] = None) -> httpx.AsyncClient:
        """
        Create HTTP client with mTLS configuration.
        
        In production, this uses actual certificates for secure communication.
        """
        timeout_value = timeout or self.descriptor.timeout_seconds
        
        client_kwargs = {
            "timeout": timeout_value,
            "headers": {
                "User-Agent": "Aetherion-Function-Broker/1.0",
                "X-Service-ID": "function-broker"
            }
        }
        
        # Add mTLS if required
        if self.descriptor.requires_mtls:
            if self.settings.ca_bundle:
                client_kwargs["verify"] = self.settings.ca_bundle
            
            if self.settings.client_cert and self.settings.client_key:
                client_kwargs["cert"] = (
                    self.settings.client_cert,
                    self.settings.client_key
                )
        
        return httpx.AsyncClient(**client_kwargs)

    def _add_trace_headers(self, envelope: Envelope) -> dict[str, str]:
        """Extract trace headers from envelope context"""
        headers = {}
        
        if "trace_id" in envelope.context:
            headers["X-Trace-ID"] = envelope.context["trace_id"]
        
        if "span_id" in envelope.context:
            headers["X-Span-ID"] = envelope.context["span_id"]
        
        headers["X-Request-ID"] = envelope.request_id
        headers["X-Tenant-ID"] = envelope.tenant_id
        headers["X-Actor"] = envelope.actor
        
        return headers

    async def _call_http_engine(
        self,
        payload: dict,
        envelope: Envelope
    ) -> dict:
        """
        Generic HTTP engine caller with retry logic.
        
        This handles common HTTP patterns and error cases.
        """
        if not self.descriptor.endpoint:
            raise ValueError(f"No endpoint configured for {self.descriptor.id}")
        
        headers = self._add_trace_headers(envelope)
        
        # Retry logic
        max_attempts = self.descriptor.retry_policy.get("max_attempts", 3)
        
        last_error = None
        for attempt in range(max_attempts):
            try:
                async with self._create_http_client() as client:
                    self.logger.debug(
                        f"Calling {self.descriptor.endpoint} (attempt {attempt + 1}/{max_attempts})"
                    )
                    
                    response = await client.post(
                        str(self.descriptor.endpoint),
                        json=payload,
                        headers=headers
                    )
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                last_error = e
                self.logger.warning(
                    f"HTTP error {e.response.status_code} on attempt {attempt + 1}: {e}"
                )
                
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    break
                    
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                self.logger.warning(f"Network error on attempt {attempt + 1}: {e}")
        
        # All attempts failed
        self.logger.error(f"All {max_attempts} attempts failed for {self.descriptor.id}")
        raise RuntimeError(f"Engine call failed after {max_attempts} attempts") from last_error

    def _sanitize_engine_response(self, response: dict) -> dict:
        """
        Sanitize engine response to remove internal details.
        
        CRITICAL: This prevents exposure of:
        - Stack traces
        - Source code references
        - Internal database schemas
        - Policy logic
        - Model weights or parameters
        """
        # Remove any keys that might expose internals
        dangerous_keys = {
            "stack_trace",
            "traceback",
            "exception",
            "sql_query",
            "db_schema",
            "policy_text",
            "rego_source",
            "model_weights",
            "internal_state",
            "_internal",
            "__private"
        }
        
        sanitized = {}
        for key, value in response.items():
            if key.lower() in dangerous_keys or key.startswith("_"):
                continue
            sanitized[key] = value
        
        return sanitized
