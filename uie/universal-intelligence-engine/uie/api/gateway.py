"""
UIE API Gateway

FastAPI endpoints for:
- /v1/submit: Submit new request
- /v1/continue: Continue clarification loop
- /v1/status: Check request status

All endpoints enforce OPA policies and proper security.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Union
from pydantic import BaseModel
import uuid
import json
import logging
from datetime import datetime

from uie.core.schemas import (
    Envelope, NormalizedResult, validate_envelope,
    create_normalized_result, Usage
)
from uie.security.policy_enforcement import (
    OPAClient, PolicyEnforcer, PolicyDecision
)
from uie.core.intent_understanding import IntentEnhancer
from uie.observability.tracing import TracingManager
from uie.observability.metrics import MetricsCollector
from uie.core.orchestrator import QueryOrchestrator

# Configure logger
logger = logging.getLogger(__name__)

class OrchestrateRequest(BaseModel):
    input: str
    session_id: Optional[str] = None

class SimpleSubmitRequest(BaseModel):
    input: str

# Initialize FastAPI app
app = FastAPI(
    title="Universal Intelligence Engine",
    description="Middleware connecting AI applications to Collective General Intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_opa_client():
    """Dependency: OPA client."""
    client = OPAClient()
    try:
        yield client
    finally:
        await client.close()


async def get_policy_enforcer(opa_client: OPAClient = Depends(get_opa_client)):
    """Dependency: Policy enforcer."""
    return PolicyEnforcer(opa_client)


async def get_intent_enhancer():
    """Dependency: Intent enhancer."""
    return IntentEnhancer()


async def get_tracing_manager():
    """Dependency: Tracing manager."""
    return TracingManager()


async def get_metrics_collector():
    """Dependency: Metrics collector."""
    return MetricsCollector()


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_trace_id(request, call_next):
    """Add trace ID to all requests."""
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    
    return response


@app.middleware("http")
async def timing_middleware(request, call_next):
    """Track request timing."""
    start_time = datetime.utcnow()
    response = await call_next(request)
    
    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    
    return response


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "uie",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/v1/status/{request_id}")
async def get_status(
    request_id: str,
    tracing: TracingManager = Depends(get_tracing_manager)
):
    """
    Get status of a request.
    
    Returns current processing status and any partial results.
    """
    with tracing.span("get_status"):
        # Query status from orchestrator
        # (Implementation would check Redis or database)
        
        return JSONResponse({
            "request_id": request_id,
            "status": "processing",
            "message": "Request is being processed"
        })


async def _process_envelope(
    envelope: Union[Envelope, dict],
    x_api_key: Optional[str] = None,
) -> NormalizedResult:
    """
    Shared orchestration logic for any Envelope-based callers.
    Accepts either:
      - raw dict that matches Envelope schema, or
      - an already-constructed Envelope instance.
    """

    try:
        if isinstance(envelope, Envelope):
            validated = envelope
        else:
            validated = validate_envelope(envelope)

        orchestrator = QueryOrchestrator()
        result = await orchestrator.execute(validated)

        # Normalize output for terminal-friendly responses
        try:
            if hasattr(result, "dict"):
                return result.dict()
            return result
        except Exception:
            return result
    except Exception as e:
        logger.error("[_process_envelope] envelope=%s", envelope, exc_info=True)
        raise

@app.post("/v1/submit", response_model=NormalizedResult)
async def submit_request(
    envelope: Envelope,
    x_api_key: Optional[str] = Header(default=None),
    policy_enforcer: PolicyEnforcer = Depends(get_policy_enforcer),
    intent_enhancer: IntentEnhancer = Depends(get_intent_enhancer),
    tracing: TracingManager = Depends(get_tracing_manager),
    metrics: MetricsCollector = Depends(get_metrics_collector),
):
    # you can still run policy checks etc. here if needed

    return await _process_envelope(envelope, x_api_key=x_api_key)

@app.post("/v1/simple-submit")
async def simple_submit(
    body: SimpleSubmitRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Public-friendly entrypoint for UIE.

    Accepts:
      { "input": "..." }

    Internally wraps it into an Envelope-like dict and reuses the same pipeline.
    """
    envelope_data = {
        "tenant_id": "public-dev",

        "actor": "aetherion-lite-user",

        "intent": {
            "type": "freeform_request",
            "task": "general_query",
            "topic": "general",
            "urgency": "normal",
            "target_engine": "uie",
            "domains": [],
        },

        "payload": {
            "input": body.input,
            "text": body.input,
            "json_data": {},
            "context": {},
        },
        
        "context_refs": [],
        # optional trace_id; validator/orchestrator may also generate this
        "trace_id": str(uuid.uuid4()),
    }

    try:
        return await _process_envelope(envelope_data, x_api_key=x_api_key)
    except Exception as e:
        logger.error("[/v1/simple-submit] Internal error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal UIE error")

    """
    Submit a new request to UIE.
    
    Request body should conform to Envelope schema.
    Returns NormalizedResult or clarification request.
    """
    start_time = datetime.utcnow()
    
    with tracing.span("submit_request") as span:
        try:
            # 1. Validate envelope
            span.add_event("validating_envelope")
            try:
                envelope = validate_envelope(request_data)
            except Exception as e:
                metrics.increment("validation_errors")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid envelope: {str(e)}"
                )
            
            # 2. Enhance intent if needed
            span.add_event("enhancing_intent")
            envelope = intent_enhancer.enhance(envelope)
            
            # 3. Pre-call OPA check
            span.add_event("checking_ingress_policy")
            ingress_policy = await policy_enforcer.enforce_ingress(envelope)
            
            if ingress_policy.decision == PolicyDecision.DENY:
                metrics.increment("policy_denials")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Policy violation: {', '.join(ingress_policy.violations)}"
                )
            
            # 4. Apply masking if needed
            if ingress_policy.decision == PolicyDecision.MASK:
                span.add_event("applying_masking")
                envelope = policy_enforcer.apply_masking(
                    envelope,
                    ingress_policy.masked_fields
                )
            
            # 5. Log audit trail
            span.add_event("logging_audit")
            span.set_attribute("tenant_id", envelope.tenant_id)
            span.set_attribute("policy_digest", ingress_policy.policy_digest)
            
            # 6. Forward to orchestrator
            span.add_event("forwarding_to_orchestrator")
            
            # Import orchestrator here to avoid circular dependency
            from uie.core.orchestrator import QueryOrchestrator
            orchestrator = QueryOrchestrator()
            
            result = await orchestrator.execute(envelope)
            
            # 7. Pre-publish OPA check
            span.add_event("checking_egress_policy")
            egress_policy = await policy_enforcer.enforce_egress(envelope, result)
            
            if egress_policy.decision == PolicyDecision.DENY:
                metrics.increment("egress_policy_denials")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Egress policy violation: {', '.join(egress_policy.violations)}"
                )
            
            # 8. Apply final redaction if needed
            if egress_policy.decision == PolicyDecision.MASK:
                span.add_event("applying_redaction")
                result = policy_enforcer.apply_redaction(
                    result,
                    egress_policy.masked_fields
                )
            
            # 9. Record metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            metrics.record_latency("submit_request", duration_ms)
            metrics.increment("requests_completed")
            metrics.record_tokens(
                "input",
                result.usage.input_tokens
            )
            metrics.record_tokens(
                "output",
                result.usage.output_tokens
            )
            
            # 10. Return result
            return result.dict()
        
        except HTTPException:
            raise
        except Exception as e:
            metrics.increment("internal_errors")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(e)}"
            )


@app.post("/v1/continue")
async def continue_request(
    continuation_data: dict,
    policy_enforcer: PolicyEnforcer = Depends(get_policy_enforcer),
    tracing: TracingManager = Depends(get_tracing_manager),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """
    Continue a clarification loop.
    
    Request should include:
    - thread_id: From previous clarification
    - continuation_data: User's answers to clarification questions
    """
    with tracing.span("continue_request") as span:
        try:
            # 1. Validate continuation
            thread_id = continuation_data.get("thread_id")
            if not thread_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing thread_id"
                )
            
            # 2. Retrieve stored state from Redis
            span.add_event("retrieving_thread_state")
            from uie.core.clarification import ClarificationManager
            clarification_mgr = ClarificationManager()
            
            envelope = await clarification_mgr.get_thread_state(thread_id)
            if not envelope:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {thread_id} not found or expired"
                )
            
            # 3. Merge continuation data into envelope
            span.add_event("merging_continuation_data")
            envelope.continuation_data = continuation_data.get("data", {})
            envelope.thread_id = thread_id
            
            # 4. Resume orchestration
            span.add_event("resuming_orchestration")
            from uie.core.orchestrator import QueryOrchestrator
            orchestrator = QueryOrchestrator()
            
            result = await orchestrator.resume(envelope)
            
            # 5. Check egress policy
            egress_policy = await policy_enforcer.enforce_egress(envelope, result)
            
            if egress_policy.decision == PolicyDecision.DENY:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Egress policy violation: {', '.join(egress_policy.violations)}"
                )
            
            if egress_policy.decision == PolicyDecision.MASK:
                result = policy_enforcer.apply_redaction(
                    result,
                    egress_policy.masked_fields
                )
            
            # 6. Clean up thread state if completed
            if result.status == "completed":
                await clarification_mgr.delete_thread_state(thread_id)
            
            metrics.increment("continuations_completed")
            
            return result.dict()
        
        except HTTPException:
            raise
        except Exception as e:
            metrics.increment("internal_errors")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(e)}"
            )

@app.post("/orchestrate")
async def orchestrate(
    request: dict,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Thin wrapper endpoint for CustomGPT.

    Accepts:
      {
        "input": "some text",
        "session_id": "optional string"
      }

    Wraps that into a proper Envelope and sends it through the same UIE pipeline.
    """
    try:
        input_text = request.get("input")
        if not input_text or not isinstance(input_text, str):
            raise HTTPException(status_code=400, detail="Missing or invalid 'input' field")

        envelope_data = {
            "tenant_id": "public-dev",

            "actor": "aetherion-lite-user",

            "intent": {
                "type": "freeform_request",
                "task": "general_query",
                "topic": "general",
                "urgency": "normal",
                "target_engine": "uie",
                "domains": [],
            },

            "payload": {
                "input": input_text,
                "text": input_text,
                "json_data": {},
                "context": {
                    "session_id": request.get("session_id"),
                    "source": "aetherion_lite_terminal",
                },
            },

            "context_refs": [],
            "trace_id": str(uuid.uuid4()),
        }

        return await _process_envelope(envelope_data, x_api_key=x_api_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/orchestrate] Internal error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal UIE error")


# (Optional) if you had this before, keep it or comment it out – but it's **not** required
# @app.exception_handler(500)
# async def internal_error_handler(request, exc):
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": "internal_error",
#             "message": "An internal error occurred",
#             "trace_id": getattr(request.state, "trace_id", None),
#         },
#     )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logging.info("UIE starting up...")
    
    # Load catalogs
    from uie.catalogs.loader import CatalogLoader
    from pathlib import Path
    
    loader = CatalogLoader(Path("config"))
    loader.load_all()
    
    # Store in app state
    app.state.catalog_loader = loader
    
    logging.info("UIE ready")
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logging.info("UIE shutting down...")
