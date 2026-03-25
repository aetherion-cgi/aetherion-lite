"""
CEOA FastAPI Application - Main API Server

This is the entry point for the Compute & Energy Orchestration API.
It orchestrates all components: scheduler, carbon intelligence, cloud adapters,
governance, and observability.

Lean architecture: ~400 LOC for main app vs. ~1,500+ LOC in bloated approach.
"""
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis
import yaml
import logging
import os
from pathlib import Path
logger = logging.getLogger(__name__)

LOCAL_MODE = os.getenv("CEOA_LOCAL_MODE", "true").lower() == "true"
CONFIG_DIR = Path(__file__).resolve().parent / "configs"



# Internal imports (would be actual imports in production)
# from backend.models import Workload, WorkloadStatus
# from backend.scheduler.core import greedy_select_placement, CONFIG
# from backend.carbon.engine import CarbonIntelligenceEngine
# from backend.adapters.cloud_providers import get_adapter
# from backend.observability.kit import (
#     setup_fastapi_observability,
#     track_workload_submission,
#     track_workload_completion,
#     get_logger
# )


# ============================================================================
# APPLICATION SETUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - setup and teardown.
    
    Runs on startup and shutdown.
    """
    # Startup
    logger.info("Starting CEOA API server")
    
    # Initialize global resources
    app.state.redis = None
    app.state.carbon_engine = None

    if LOCAL_MODE:
        logger.info("CEOA local mode enabled: skipping Redis and CarbonIntelligenceEngine startup")
    else:
        app.state.redis = Redis(host="redis", port=6379, decode_responses=True)
        from backend.carbon.engine import CarbonIntelligenceEngine
        app.state.carbon_engine = CarbonIntelligenceEngine(
            api_keys={
                "electricity_maps": "dummy_key",  # Would load from env
            },
            redis_client=app.state.redis,
        )

    # Load scheduler config
    config_path = CONFIG_DIR / "scheduler.yaml"
    if config_path.exists():
        with open(config_path) as f:
            app.state.scheduler_config = yaml.safe_load(f)
    else:
        logger.warning(f"Scheduler config not found at {config_path}; using empty config")
        app.state.scheduler_config = {}
    
    logger.info("CEOA API server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CEOA API server")
    if app.state.redis is not None:
        app.state.redis.close()


# Create FastAPI app
app = FastAPI(
    title="Compute & Energy Orchestration API",
    description="Aetherion's infrastructure layer for intelligent compute orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Setup observability (Prometheus + OpenTelemetry)
# setup_fastapi_observability(app, "ceoa-api", otlp_endpoint="localhost:4317")

# Get structured logger
# logger = get_logger("ceoa.api")


@app.get("/health")
async def health_check():
    """Simple service health endpoint for local activation and broker testing."""
    return {
        "status": "healthy",
        "service": "ceoa",
        "mode": "local" if LOCAL_MODE else "production",
    }


# ============================================================================
# WORKLOAD ENDPOINTS
# ============================================================================

class ResourceRequirements(BaseModel):
    cpu_cores: float = Field(gt=0)
    memory_gb: float = Field(gt=0)
    gpu_required: bool = False
    gpu_type: Optional[str] = None
    estimated_duration_minutes: int = Field(default=30, gt=0)


class SchedulingPreferences(BaseModel):
    carbon_aware: bool = True
    carbon_weight: float = Field(default=0.5, ge=0, le=1)
    cost_optimize: bool = True
    max_delay_hours: int = Field(default=0, ge=0)
    preferred_regions: List[str] = []
    sovereignty_requirements: List[str] = []


class WorkloadSubmissionRequest(BaseModel):
    description: str
    docker_image: str
    requirements: ResourceRequirements
    preferences: SchedulingPreferences = SchedulingPreferences()
    data_sources: List[str] = []


class WorkloadResponse(BaseModel):
    id: UUID
    status: str
    placement: Optional[dict] = None
    estimates: Optional[dict] = None
    created_at: str


class PlacementRecommendationResponse(BaseModel):
    primary: dict
    alternatives: List[dict]
    reasoning: str


class CarbonIntensityResponse(BaseModel):
    region: str
    intensity_gco2_kwh: float
    is_green_window: bool


# ============================================================================
# WORKLOAD ENDPOINTS
# ============================================================================

@app.post("/ceoa/v1/workloads", response_model=WorkloadResponse, status_code=status.HTTP_201_CREATED)
# @track_workload_submission
async def submit_workload(request: WorkloadSubmissionRequest):
    """
    Submit workload for execution.
    
    Flow:
    1. Validate request
    2. Get available infrastructure
    3. Get carbon data
    4. Run placement optimization
    5. Evaluate governance
    6. Submit to cloud provider
    7. Return workload details
    """
    try:
        # Generate workload ID
        workload_id = uuid4()
        
        # Simulate workload submission
        # In production:
        # 1. Query available infrastructure nodes
        # 2. Get carbon data for regions
        # 3. Run scheduler to find optimal placement
        # 4. Evaluate governance policies (OPA)
        # 5. Submit job via cloud adapter
        # 6. Save to database
        
        return WorkloadResponse(
            id=workload_id,
            status="pending",
            placement=None,
            estimates={
                "cost_usd": 2.50,
                "carbon_kg": 0.15,
                "duration_seconds": 1800,
            },
            created_at="2025-01-01T00:00:00Z"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit workload: {str(e)}"
        )


@app.get("/ceoa/v1/workloads/{workload_id}", response_model=WorkloadResponse)
async def get_workload(workload_id: UUID):
    """Get workload status and details"""
    # In production: Query database for workload
    # For now: Return mock response
    
    return WorkloadResponse(
        id=workload_id,
        status="completed",
        placement={
            "provider": "aws",
            "region": "us-west-2",
            "node_id": "node-123",
        },
        estimates={
            "cost_usd": 2.50,
            "carbon_kg": 0.15,
        },
        created_at="2025-01-01T00:00:00Z"
    )


@app.delete("/ceoa/v1/workloads/{workload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_workload(workload_id: UUID):
    """Cancel running workload"""
    # In production:
    # 1. Check workload status
    # 2. Call cloud adapter to cancel job
    # 3. Update database
    return


# ============================================================================
# PLACEMENT ENDPOINTS
# ============================================================================

@app.post("/ceoa/v1/placement/optimize", response_model=PlacementRecommendationResponse)
async def optimize_placement(request: WorkloadSubmissionRequest):
    """
    Get optimal placement recommendation without submitting workload.
    
    Useful for "what-if" analysis and cost estimation.
    """
    # In production:
    # 1. Get available infrastructure
    # 2. Get carbon data
    # 3. Run scheduler
    # 4. Return recommendations
    
    return PlacementRecommendationResponse(
        primary={
            "provider": "aws",
            "region": "us-west-2",
            "instance_type": "c6i.xlarge",
            "spot_instance": True,
            "estimated_cost": 1.20,
            "estimated_carbon": 0.08,
            "placement_score": 0.87,
        },
        alternatives=[
            {
                "provider": "gcp",
                "region": "us-west1",
                "instance_type": "n2-standard-4",
                "placement_score": 0.82,
            }
        ],
        reasoning="Selected us-west-2 due to low carbon intensity and spot availability"
    )


# ============================================================================
# DEVICE MESH ENDPOINTS
# ============================================================================

@app.post("/ceoa/v1/devices", status_code=status.HTTP_201_CREATED)
async def register_device(device_info: dict, preferences: dict):
    """Register device for mesh participation"""
    device_id = uuid4()
    
    # In production:
    # 1. Validate device info
    # 2. Save to database
    # 3. Add to device mesh coordination
    
    return {
        "id": device_id,
        "status": "active",
        "earnings": {"total_usd": 0.0},
        "registered_at": "2025-01-01T00:00:00Z"
    }


@app.get("/ceoa/v1/devices/{device_id}")
async def get_device(device_id: UUID):
    """Get device status and earnings"""
    return {
        "id": device_id,
        "status": "active",
        "earnings": {
            "total_usd": 5.23,
            "pending_usd": 0.52,
            "paid_usd": 4.71,
        },
        "statistics": {
            "workloads_completed": 127,
            "compute_hours_contributed": 45.2,
        }
    }


# ============================================================================
# ENERGY & CARBON ENDPOINTS
# ============================================================================

@app.get("/ceoa/v1/energy/carbon-intensity")
async def get_carbon_intensity(regions: List[str]):
    """
    Get current carbon intensity for regions.
    
    Uses CarbonIntelligenceEngine with caching.
    """
    # In production: Use app.state.carbon_engine
    
    result = {}
    for region in regions:
        result[region] = 150.0  # gCO2/kWh (mock)
    
    return result


@app.get("/ceoa/v1/energy/carbon-forecast")
async def get_carbon_forecast(region: str, hours: int = 24):
    """Get carbon intensity forecast"""
    # In production: Use app.state.carbon_engine.get_forecast()
    
    return [
        {
            "timestamp": "2025-01-01T01:00:00Z",
            "carbon_intensity": 140.0,
            "forecast_confidence": 0.85,
            "is_green_window": True,
        }
        # ... more forecast points
    ]


# ============================================================================
# INFRASTRUCTURE ENDPOINTS
# ============================================================================

@app.get("/ceoa/v1/infrastructure/nodes")
async def list_infrastructure_nodes(
    type: Optional[str] = None,
    region: Optional[str] = None,
    available: bool = True
):
    """List available infrastructure nodes"""
    # In production: Query database/cache for nodes
    
    return {
        "nodes": [
            {
                "id": "node-123",
                "type": "cloud",
                "provider": "aws",
                "region": "us-west-2",
                "capabilities": {
                    "cpu_cores": 4,
                    "memory_gb": 16,
                    "gpu_available": False,
                },
                "availability": {
                    "available": True,
                    "available_cpu_cores": 4,
                    "queue_length": 0,
                },
            }
        ]
    }


# ============================================================================
# GOVERNANCE ENDPOINTS
# ============================================================================

@app.post("/ceoa/v1/governance/evaluate")
async def evaluate_governance(workload_id: UUID, placement: dict):
    """
    Evaluate workload against governance policies.
    
    Uses OPA policy engine.
    """
    # In production:
    # 1. Load workload details
    # 2. Build OPA input
    # 3. Query OPA
    # 4. Return evaluation
    
    return {
        "authorized": True,
        "tier": "routine",
        "benefit_score": 0.72,
        "harm_score": 0.15,
        "sovereignty_compliant": True,
        "violations": [],
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/ceoa/v1/admin/reload-config")
async def reload_config():
    """
    Reload scheduler configuration without restarting.
    
    This is the power of config-driven architecture!
    """
    try:
        with open("configs/scheduler.yaml") as f:
            app.state.scheduler_config = yaml.safe_load(f)
        
        return {"status": "success", "message": "Configuration reloaded"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload config: {str(e)}"
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standard HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
        }
    )


# ============================================================================
# STARTUP MESSAGE
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  CEOA - Compute & Energy Orchestration API                       ║
    ║  Aetherion CGI Platform - Infrastructure Layer                   ║
    ║                                                                  ║
    ║  📊 Metrics: http://localhost:8000/metrics                       ║
    ║  📚 Docs: http://localhost:8000/docs                             ║
    ║  🏥 Health: http://localhost:8000/health                         ║
    ║                                                                  ║
    ║  🌍 Orchestrating computation across human infrastructure        ║
    ║  ⚡ Optimizing for cost, carbon, and energy efficiency           ║
    ║  🔐 Governed by constitutional principles                        ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
