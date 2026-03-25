"""
Function Broker API
FastAPI application for internal capability invocation
"""

import os
import sys
from pathlib import Path
from typing import Optional

# --- BEGIN AETHERION-COMMON PATH PATCH ---
# Goal: ensure the repo's `aetherion-common/` directory (which contains `aetherion_common/`) is on sys.path
# so imports like `from aetherion_common.schemas import ...` work even when running from subfolders.

HERE = Path(__file__).resolve()

# Allow an override if you ever relocate the repo
AETHERION_ROOT = os.environ.get("AETHERION_ROOT")

root: Path
if AETHERION_ROOT:
    root = Path(AETHERION_ROOT).expanduser().resolve()
else:
    # Walk up until we find the repo root (identified by having `aetherion-common/` and `function-broker/`)
    root = HERE
    for _ in range(10):
        if (root / "aetherion-common").exists() and (root / "function-broker").exists():
            break
        root = root.parent

COMMON_PATH = root / "aetherion-common"

# Ensure the aetherion-common project root is on sys.path
# (This path must contain the `aetherion_common/` package directory.)
if COMMON_PATH.exists() and str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))
# --- END AETHERION-COMMON PATH PATCH ---

from broker.core import (
    CapabilityRegistry,
    BrokerSecurity,
    FunctionBrokerService,
    AdapterConfig
)

from aetherion_common.schemas import Envelope, NormalizedResult

from fastapi import FastAPI, Depends, Query, Request, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional


from broker.observability import get_logger, MetricsCollector, configure_logging
from broker.config.settings import settings

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Aetherion Function Broker",
    version="1.0.0",
    description="Internal service mapping capability_id + Envelope → NormalizedResult",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc"
)

# Global service instances
_registry: Optional[CapabilityRegistry] = None
_security: Optional[BrokerSecurity] = None
_metrics: Optional[MetricsCollector] = None
_broker_service: Optional[FunctionBrokerService] = None


def get_registry() -> CapabilityRegistry:
    """Dependency: Get capability registry"""
    global _registry
    if _registry is None:
        adapter_config = AdapterConfig(
            ca_bundle=settings.ca_bundle,
            client_cert=settings.client_cert,
            client_key=settings.client_key,
            default_timeout=settings.default_timeout,
            max_retries=settings.max_retries
        )
        _registry = CapabilityRegistry(settings.capabilities_file, adapter_config)
    return _registry


def get_security() -> BrokerSecurity:
    """Dependency: Get security manager"""
    global _security
    if _security is None:
        _security = BrokerSecurity(
            internal_network_cidrs=settings.internal_network_cidrs,
            strict_mode=settings.strict_security
        )
    return _security


def get_metrics() -> MetricsCollector:
    """Dependency: Get metrics collector"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def get_broker_service() -> FunctionBrokerService:
    """Dependency: Get broker service"""
    global _broker_service
    if _broker_service is None:
        _broker_service = FunctionBrokerService(
            registry=get_registry(),
            security=get_security(),
            metrics=get_metrics()
        )
    return _broker_service


# Health check endpoint
@app.get("/health")
async def health_check(broker: FunctionBrokerService = Depends(get_broker_service)):
    """Health check endpoint"""
    return await broker.health_check()


# Main invocation endpoint
@app.post("/v1/invoke", response_model=NormalizedResult)
async def invoke_capability(
    capability_id: str = Query(..., description="Capability ID to invoke"),
    envelope: Envelope = ...,
    request: Request = ...,
    broker: FunctionBrokerService = Depends(get_broker_service)
) -> NormalizedResult:
    """
    Invoke a capability with the given envelope.
    
    SECURITY: This endpoint is INTERNAL ONLY.
    - Requires mTLS authentication
    - Only accessible from service mesh
    - Never exposed to public internet
    
    Args:
        capability_id: The capability to invoke (e.g., 'bue.underwrite')
        envelope: Universal request envelope
        request: FastAPI request object (for security checks)
        broker: Broker service instance
    
    Returns:
        NormalizedResult with sanitized response data
    """
    logger.info(
        f"Invoke request: capability={capability_id}, "
        f"tenant={envelope.tenant_id}, actor={envelope.actor}"
    )
    
    try:
        result = await broker.invoke(capability_id, envelope, request)
        return result
        
    except Exception as e:
        logger.exception("Unexpected error in invoke endpoint")
        raise


# List capabilities endpoint
@app.get("/v1/capabilities")
async def list_capabilities(
    request: Request,
    tenant_id: str = Query(..., description="Tenant ID"),
    actor: str = Query(..., description="Actor ID"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    security: BrokerSecurity = Depends(get_security),
    broker: FunctionBrokerService = Depends(get_broker_service)
) -> dict:
    """
    List available capabilities for a tenant/actor.
    
    Returns sanitized capability information (no internal details).
    """
    # Security check
    try:
        security.check_internal_call(request)
    except Exception as e:
        logger.warning(f"Unauthorized capabilities list request: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    
    capabilities = await broker.list_capabilities(tenant_id, actor, domain)
    
    return {
        "capabilities": capabilities,
        "count": len(capabilities),
        "tenant_id": tenant_id
    }


# Metrics endpoint (Prometheus format)
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics(
    metrics_collector: MetricsCollector = Depends(get_metrics)
) -> str:
    """
    Prometheus metrics endpoint.
    
    In production, this is scraped by Prometheus for monitoring.
    """
    return metrics_collector.export_prometheus()


# Debug endpoint (development only)
@app.get("/debug/metrics")
async def debug_metrics(
    metrics_collector: MetricsCollector = Depends(get_metrics)
) -> dict:
    """Debug endpoint to view all metrics (development only)"""
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")
    
    return metrics_collector.get_all_metrics()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Function Broker")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Capabilities file: {settings.capabilities_file}")
    
    # Initialize registry to load capabilities
    registry = get_registry()
    logger.info(f"Loaded {len(registry._capabilities)} capabilities")
    
    # Log security configuration
    logger.info(f"Strict security: {settings.strict_security}")
    logger.info(f"mTLS required: {settings.require_mtls}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Function Broker")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with sanitized responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "category": "client" if exc.status_code < 500 else "server"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with sanitized responses"""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An error occurred during processing",
                "category": "server"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
