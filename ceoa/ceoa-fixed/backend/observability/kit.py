"""
Observability Kit - Shared monitoring library for CEOA.

Strategy: One tiny shared lib with Prometheus counters/histograms + OTel middleware.
Reuse everywhere. Dashboards are JSON (Grafana), not Python.

~200-300 LOC vs. ~1,000+ LOC scattered monitoring code.
"""
from functools import wraps
from time import time
from typing import Callable, Optional
import logging

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Use custom registry to avoid conflicts
REGISTRY = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    'ceoa_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    'ceoa_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Workload metrics
workloads_submitted_total = Counter(
    'ceoa_workloads_submitted_total',
    'Total workloads submitted',
    ['tenant_id'],
    registry=REGISTRY
)

workloads_completed_total = Counter(
    'ceoa_workloads_completed_total',
    'Total workloads completed',
    ['tenant_id', 'status'],
    registry=REGISTRY
)

workload_duration_seconds = Histogram(
    'ceoa_workload_duration_seconds',
    'Workload execution duration in seconds',
    ['provider', 'region'],
    registry=REGISTRY,
    buckets=[10, 30, 60, 300, 600, 1800, 3600, 7200, 14400, 28800]  # 10s to 8hr
)

workload_cost_usd = Histogram(
    'ceoa_workload_cost_usd',
    'Workload cost in USD',
    ['provider', 'region'],
    registry=REGISTRY,
    buckets=[0.01, 0.1, 1, 10, 100, 1000, 10000]
)

workload_carbon_kg = Histogram(
    'ceoa_workload_carbon_kg',
    'Workload carbon footprint in kg CO2',
    ['provider', 'region'],
    registry=REGISTRY,
    buckets=[0.01, 0.1, 1, 10, 100, 1000]
)

# Placement metrics
placement_decisions_total = Counter(
    'ceoa_placement_decisions_total',
    'Total placement decisions',
    registry=REGISTRY
)

placement_score = Histogram(
    'ceoa_placement_score',
    'Placement score (0-1)',
    registry=REGISTRY,
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

placement_failures_total = Counter(
    'ceoa_placement_failures_total',
    'Total placement failures',
    ['reason'],
    registry=REGISTRY
)

# Carbon metrics
carbon_intensity = Gauge(
    'ceoa_carbon_intensity_gco2_kwh',
    'Current carbon intensity in gCO2/kWh',
    ['region'],
    registry=REGISTRY
)

green_window_active = Gauge(
    'ceoa_green_window_active',
    'Whether region is in green window (1=yes, 0=no)',
    ['region'],
    registry=REGISTRY
)

# Device mesh metrics
device_mesh_active_devices = Gauge(
    'ceoa_device_mesh_active_devices',
    'Number of active devices in mesh',
    registry=REGISTRY
)

device_mesh_workloads_total = Counter(
    'ceoa_device_mesh_workloads_total',
    'Total workloads executed on device mesh',
    registry=REGISTRY
)

# Infrastructure metrics
infrastructure_nodes_available = Gauge(
    'ceoa_infrastructure_nodes_available',
    'Number of available infrastructure nodes',
    ['provider', 'type'],
    registry=REGISTRY
)


# ============================================================================
# OPENTELEMETRY SETUP
# ============================================================================

def setup_tracing(service_name: str, otlp_endpoint: Optional[str] = None) -> None:
    """
    Setup OpenTelemetry distributed tracing.
    
    Args:
        service_name: Name of the service (ceoa-api, ceoa-scheduler, etc)
        otlp_endpoint: OTLP collector endpoint (e.g., "localhost:4317")
    """
    provider = TracerProvider()
    
    if otlp_endpoint:
        # Export to OTLP collector (Jaeger, Tempo, etc.)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    
    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for instrumenting code"""
    return trace.get_tracer(name)


# ============================================================================
# FASTAPI MIDDLEWARE
# ============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically record HTTP metrics.
    
    Usage:
        app.add_middleware(MetricsMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response


def setup_fastapi_observability(
    app: FastAPI,
    service_name: str,
    otlp_endpoint: Optional[str] = None
) -> None:
    """
    Setup complete observability for FastAPI app.
    
    Adds:
    - Prometheus metrics endpoint
    - Metrics middleware
    - OpenTelemetry tracing
    
    Usage:
        app = FastAPI()
        setup_fastapi_observability(app, "ceoa-api")
    """
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        from starlette.responses import Response
        return Response(
            generate_latest(REGISTRY),
            media_type="text/plain"
        )
    
    # Setup tracing
    setup_tracing(service_name, otlp_endpoint)
    FastAPIInstrumentor.instrument_app(app)
    
    # Add health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": service_name}


# ============================================================================
# DECORATORS FOR CUSTOM METRICS
# ============================================================================

def track_workload_submission(func: Callable) -> Callable:
    """Decorator to track workload submissions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract tenant_id from kwargs if available
        tenant_id = kwargs.get("tenant_id", "unknown")
        
        # Increment counter
        workloads_submitted_total.labels(tenant_id=tenant_id).inc()
        
        # Call original function
        return await func(*args, **kwargs)
    
    return wrapper


def track_workload_completion(func: Callable) -> Callable:
    """Decorator to track workload completions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        # Extract metrics from result
        if isinstance(result, dict):
            tenant_id = result.get("tenant_id", "unknown")
            status = result.get("status", "unknown")
            provider = result.get("placement", {}).get("provider", "unknown")
            region = result.get("placement", {}).get("region", "unknown")
            
            # Record completion
            workloads_completed_total.labels(
                tenant_id=tenant_id,
                status=status
            ).inc()
            
            # Record duration if available
            if "actual" in result and "duration_seconds" in result["actual"]:
                workload_duration_seconds.labels(
                    provider=provider,
                    region=region
                ).observe(result["actual"]["duration_seconds"])
            
            # Record cost if available
            if "actual" in result and "cost_usd" in result["actual"]:
                workload_cost_usd.labels(
                    provider=provider,
                    region=region
                ).observe(result["actual"]["cost_usd"])
            
            # Record carbon if available
            if "actual" in result and "carbon_kg" in result["actual"]:
                workload_carbon_kg.labels(
                    provider=provider,
                    region=region
                ).observe(result["actual"]["carbon_kg"])
        
        return result
    
    return wrapper


def track_placement_decision(func: Callable) -> Callable:
    """Decorator to track placement decisions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        placement_decisions_total.inc()
        
        try:
            result = await func(*args, **kwargs)
            
            # Record placement score if available
            if isinstance(result, dict) and "score" in result:
                placement_score.observe(result["score"])
            
            return result
        
        except Exception as e:
            # Record failure
            placement_failures_total.labels(reason=type(e).__name__).inc()
            raise
    
    return wrapper


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for a component.
    
    Logs are JSON-formatted for easy parsing by log aggregators.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Use JSON formatter for structured logs
    # (In production, would use python-json-logger)
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of observability kit:
    
    from observability import setup_fastapi_observability, track_workload_submission
    
    app = FastAPI()
    setup_fastapi_observability(app, "ceoa-api", otlp_endpoint="localhost:4317")
    
    @app.post("/workloads")
    @track_workload_submission
    async def submit_workload(workload: dict, tenant_id: str):
        # Your code here
        pass
    
    # Metrics available at /metrics
    # Traces sent to OTLP collector
    # Logs structured as JSON
    """
    pass
