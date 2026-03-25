"""
Aetherion UIE - Main FastAPI Application
Single public endpoint absorbing all Cortex Gateway functionality
Port 8000 for CustomGPT/Claude integration
"""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api_models import (
    AetherionRequest,
    AetherionResponse,
    HealthStatus,
    ErrorResponse
)
from security import verify_api_key, check_rate_limit, input_validator
from orchestrator import UIEOrchestrator
from function_broker_client import get_broker_client
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("=" * 80)
    logger.info("Starting Aetherion UIE (Universal Intelligence Engine)")
    logger.info(f"Mode: {config.mode}")
    logger.info(f"Port: {config.port} (PUBLIC)")
    logger.info(f"Function Broker: {config.function_broker_url}")
    logger.info(f"mTLS: {'Enabled' if config.mtls_enabled else 'Disabled'}")
    logger.info(f"Governance: {'Enabled' if config.governance_enabled else 'Disabled'}")
    logger.info("=" * 80)
    
    # Initialize broker client
    broker = get_broker_client()
    
    # Check connectivity to Function Broker
    try:
        health = await broker.health_check()
        logger.info(f"Function Broker health: {health['status']}")
    except Exception as e:
        logger.error(f"Function Broker not reachable: {e}")
        logger.warning("UIE will start but may not be able to process requests")
    
    yield
    
    # Cleanup
    logger.info("Shutting down UIE...")
    await broker.close()
    logger.info("UIE shutdown complete")


# ============================================================================
# CREATE APPLICATION
# ============================================================================

app = FastAPI(
    title="Aetherion UIE",
    description="Universal Intelligence Engine - Single endpoint for all Aetherion capabilities",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.mode == "public" else None,  # Disable docs in production if needed
    redoc_url="/redoc" if config.mode == "public" else None
)

# Add CORS middleware for web integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            details={"message": str(exc)}
        ).dict()
    )


# ============================================================================
# MAIN ENDPOINT - THE ONLY PUBLIC ROUTE
# ============================================================================

@app.post(
    "/aetherion",
    response_model=AetherionResponse,
    summary="Universal Aetherion Endpoint",
    description="""
    Single endpoint for all Aetherion capabilities.
    
    Accepts natural language or structured requests.
    Routes internally to appropriate engines via Function Broker.
    
    Perfect for CustomGPT and Claude integrations.
    """
)
async def aetherion_endpoint(
    request: AetherionRequest,
    user_id: str = Depends(verify_api_key),
    _: None = Depends(check_rate_limit)
) -> AetherionResponse:
    """
    Main endpoint - processes all requests.
    
    Natural language example:
    ```json
    {
      "message": "What happens if fusion energy becomes commercial by 2030?",
      "session_id": "user-123-session-456"
    }
    ```
    
    Structured example (legacy):
    ```json
    {
      "capability": "finance.underwrite",
      "params": {"deal": {...}},
      "response_format": "structured"
    }
    ```
    """
    # Validate input
    if request.message:
        valid, error = input_validator.validate_message(request.message)
        if not valid:
            raise HTTPException(status_code=400, detail=error)
    
    # Sanitize session ID
    if request.session_id:
        request.session_id = input_validator.sanitize_session_id(request.session_id)
    
    # Process via orchestrator
    orchestrator = UIEOrchestrator()
    response = await orchestrator.process_request(request, user_id)
    
    return response


# ============================================================================
# HEALTH & MONITORING ENDPOINTS
# ============================================================================

@app.get(
    "/health",
    response_model=HealthStatus,
    summary="Health Check",
    description="Check UIE and dependent services health"
)
async def health_check():
    """Health check endpoint"""
    broker = get_broker_client()
    broker_health = await broker.health_check()
    
    # Determine overall health
    services_healthy = broker_health.get("status") == "healthy"
    overall_status = "healthy" if services_healthy else "degraded"
    
    return HealthStatus(
        status=overall_status,
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "function_broker": broker_health.get("status", "unknown")
        },
        details={
            "mode": config.mode,
            "governance_enabled": config.governance_enabled,
            "mtls_enabled": config.mtls_enabled
        }
    )


@app.get(
    "/",
    summary="Root",
    description="Basic info about UIE"
)
async def root():
    """Root endpoint"""
    return {
        "service": "Aetherion UIE",
        "version": "2.0.0",
        "description": "Universal Intelligence Engine - The conscious interface to Aetherion",
        "endpoints": {
            "main": "/aetherion (POST)",
            "health": "/health (GET)",
            "docs": "/docs (GET)"
        },
        "integration": "Designed for CustomGPT and Claude integration",
        "architecture": "Single public endpoint, all engines protected behind Function Broker"
    }


# ============================================================================
# FOR CUSTOMGPT INTEGRATION
# ============================================================================

@app.get(
    "/.well-known/ai-plugin.json",
    summary="AI Plugin Manifest",
    description="Manifest for CustomGPT/AI plugin integration"
)
async def ai_plugin_manifest():
    """
    AI plugin manifest for CustomGPT integration.
    CustomGPT will discover capabilities through this endpoint.
    """
    return {
        "schema_version": "v1",
        "name_for_human": "Aetherion",
        "name_for_model": "aetherion",
        "description_for_human": "Universal AI platform for financial analysis, scenario modeling, and multi-domain intelligence",
        "description_for_model": "Aetherion provides advanced capabilities for financial underwriting, scenario simulation, multi-domain analysis, compute orchestration, and strategic intelligence. Use natural language to interact with sophisticated backend engines.",
        "auth": {
            "type": "user_http",
            "authorization_type": "bearer"
        },
        "api": {
            "type": "openapi",
            "url": f"http://localhost:{config.port}/openapi.json"
        },
        "logo_url": "https://aetherion.example.com/logo.png",
        "contact_email": "support@aetherion.example.com",
        "legal_info_url": "https://aetherion.example.com/legal"
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower(),
        access_log=True
    )
