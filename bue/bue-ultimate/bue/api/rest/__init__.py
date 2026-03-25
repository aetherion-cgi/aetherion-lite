from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
import inspect

# Import BUE engine components
from bue.core.engine import BUEngine, AnalysisMode

app = FastAPI(title="BUE REST API", version="1.0.0")

# Initialize engine

engine = BUEngine()

SUPPORTED_ASSET_TYPES = {"saas", "software", "cre", "real_estate", "commercial_real_estate"}


def _normalize_asset_type(asset_type: str | None, default: str) -> str:
    candidate = (asset_type or default).strip().lower()
    if candidate not in SUPPORTED_ASSET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported asset_type '{candidate}'. Supported: {sorted(SUPPORTED_ASSET_TYPES)}",
        )
    return candidate


def _resolve_mode(*candidate_names: str):
    """Resolve the first matching AnalysisMode member by name or value."""
    for candidate in candidate_names:
        if not candidate:
            continue
        upper = candidate.upper()
        if hasattr(AnalysisMode, upper):
            return getattr(AnalysisMode, upper)
        for member in AnalysisMode:
            if member.name.upper() == upper or str(member.value).upper() == upper:
                return member
    return None


def _invoke_engine(payload: Dict[str, Any], mode=None):
    """Call BUEngine.analyze using the live engine signature."""
    analyze_fn = engine.analyze
    signature = inspect.signature(analyze_fn)
    params = signature.parameters
    accepts_mode = "mode" in params
    requires_asset_type = "asset_type" in params
    asset_type = payload.get("asset_type", "general")

    kwargs = {}
    if accepts_mode and mode is not None:
        kwargs["mode"] = mode

    # Engines vary: some accept `input_data`, others `data`/`payload`/`request`,
    # and some only accept the payload positionally. Some also require an
    # `asset_type` positional/keyword argument.
    if "input_data" in params:
        kwargs["input_data"] = payload
        if requires_asset_type:
            kwargs["asset_type"] = asset_type
        return analyze_fn(**kwargs)
    if "data" in params:
        kwargs["data"] = payload
        if requires_asset_type:
            kwargs["asset_type"] = asset_type
        return analyze_fn(**kwargs)
    if "payload" in params:
        kwargs["payload"] = payload
        if requires_asset_type:
            kwargs["asset_type"] = asset_type
        return analyze_fn(**kwargs)
    if "request" in params:
        kwargs["request"] = payload
        if requires_asset_type:
            kwargs["asset_type"] = asset_type
        return analyze_fn(**kwargs)

    # Fallback: pass required asset_type first when needed, then the payload.
    if requires_asset_type:
        return analyze_fn(asset_type, payload, **kwargs)
    return analyze_fn(payload, **kwargs)

# -------------------------
# Request Models
# -------------------------

class UnderwriteRequest(BaseModel):
    project: str
    capex: float
    expected_revenue: float
    asset_type: Optional[Literal["saas", "software", "cre", "real_estate", "commercial_real_estate"]] = None
    metadata: Optional[Dict[str, Any]] = None

class ScenarioRequest(BaseModel):
    scenario: str
    asset_type: Optional[Literal["saas", "software", "cre", "real_estate", "commercial_real_estate"]] = None
    metadata: Optional[Dict[str, Any]] = None

# -------------------------
# Health Check
# -------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "bue"}

# -------------------------
# Underwriting Endpoint
# -------------------------

@app.post("/api/v1/underwrite")
async def underwrite(req: UnderwriteRequest):
    try:
        mode = _resolve_mode("STANDARD", "UNDERWRITE", "UNDERWRITING")
        asset_type = _normalize_asset_type(req.asset_type, "cre")
        result = _invoke_engine(
            {
                "asset_type": asset_type,
                "project": req.project,
                "capex": req.capex,
                "expected_revenue": req.expected_revenue,
                "metadata": req.metadata or {},
                "analysis_mode": str(getattr(mode, "value", mode)).lower() if mode is not None else "standard",
            },
            mode,
        )
        if inspect.iscoroutine(result):
            result = await result

        return {
            "id": result.id,
            "timestamp": result.timestamp.isoformat() if hasattr(result.timestamp, "isoformat") else str(result.timestamp),
            "score": result.score,
            "rating": result.rating,
            "execution_time_ms": result.execution_time_ms,
            "metrics": result.metrics,
            "risk_analysis": result.risk_analysis,
            "forecast": result.forecast,
            "governance": result.governance
        }

    except Exception as e:
        detail = str(e) or repr(e)
        if detail.startswith("HTTPException("):
            raise e
        raise HTTPException(status_code=500, detail=detail)

# -------------------------
# Scenario Analysis Endpoint
# -------------------------

@app.post("/api/v1/analyze")
async def analyze(req: ScenarioRequest):
    try:
        mode = _resolve_mode("SCENARIO", "ANALYZE", "ANALYSIS", "SIMULATION")
        asset_type = _normalize_asset_type(req.asset_type, "cre")
        result = _invoke_engine(
            {
                "asset_type": asset_type,
                "scenario": req.scenario,
                "metadata": req.metadata or {},
                "analysis_mode": str(getattr(mode, "value", mode)).lower() if mode is not None else "scenario",
            },
            mode,
        )
        if inspect.iscoroutine(result):
            result = await result

        return {
            "id": result.id,
            "timestamp": result.timestamp.isoformat() if hasattr(result.timestamp, "isoformat") else str(result.timestamp),
            "score": result.score,
            "rating": result.rating,
            "execution_time_ms": result.execution_time_ms,
            "metrics": result.metrics,
            "risk_analysis": result.risk_analysis,
            "forecast": result.forecast,
            "governance": result.governance
        }

    except Exception as e:
        detail = str(e) or repr(e)
        if detail.startswith("HTTPException("):
            raise e
        raise HTTPException(status_code=500, detail=detail)