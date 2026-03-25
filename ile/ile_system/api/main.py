import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

logger = logging.getLogger("ile")
logging.basicConfig(level=logging.INFO)

LOCAL_MODE = os.getenv("ILE_LOCAL_MODE", "true").lower() == "true"

app = FastAPI(title="ILE (Internal Only)", version="0.1.0")

orchestrator = None
get_orchestrator = None
LearningEvent = None
LearningEventType = None
DomainType = None
APIType = None


@app.on_event("startup")
async def startup():
    global orchestrator, get_orchestrator, LearningEvent, LearningEventType, DomainType, APIType

    if LOCAL_MODE:
        logger.info("ILE started (local MVP mode, internal only)")
        orchestrator = None
        return

    from ile_system.orchestrator import get_orchestrator as _get_orchestrator
    from ile_system.models import (
        LearningEvent as _LearningEvent,
        LearningEventType as _LearningEventType,
        DomainType as _DomainType,
        APIType as _APIType,
    )

    get_orchestrator = _get_orchestrator
    LearningEvent = _LearningEvent
    LearningEventType = _LearningEventType
    DomainType = _DomainType
    APIType = _APIType

    orchestrator = await get_orchestrator()
    logger.info("ILE started (full internal mode)")


@app.on_event("shutdown")
async def shutdown():
    logger.info("ILE shutting down")


class LearnRequest(BaseModel):
    observation: Dict[str, Any]
    domain: Optional[str] = "task_based"
    api: Optional[str] = "bue"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    feedback: Dict[str, Any]
    domain: Optional[str] = "user_interaction"
    api: Optional[str] = "uie"
    metadata: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ile",
        "internal": True,
        "mode": "local" if LOCAL_MODE else "full",
    }


@app.post("/v1/learn")
async def learn(req: LearnRequest):
    try:
        if LOCAL_MODE or orchestrator is None:
            return {
                "status": "accepted",
                "result": {
                    "status": "queued",
                    "task_id": f"local-learn-{abs(hash(str(req.observation))) % 10_000_000}",
                    "mode": "local",
                    "domain": req.domain,
                    "api": req.api,
                    "message": "ILE local MVP mode accepted learning event",
                },
            }

        event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType(req.domain),
            api=APIType(req.api),
            inputs=req.observation,
            metadata=req.metadata,
        )

        result = await orchestrator.process_learning_event(event, priority=6)

        return {
            "status": "accepted",
            "result": result,
        }

    except Exception as e:
        logger.error(f"ILE learn error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) or repr(e))


@app.post("/v1/feedback")
async def feedback(req: FeedbackRequest):
    try:
        if LOCAL_MODE or orchestrator is None:
            return {
                "status": "accepted",
                "result": {
                    "status": "queued",
                    "task_id": f"local-feedback-{abs(hash(str(req.feedback))) % 10_000_000}",
                    "mode": "local",
                    "domain": req.domain,
                    "api": req.api,
                    "message": "ILE local MVP mode accepted feedback event",
                },
            }

        event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType(req.domain),
            api=APIType(req.api),
            inputs=req.feedback,
            metadata=req.metadata,
        )

        result = await orchestrator.process_learning_event(event, priority=7)

        return {
            "status": "accepted",
            "result": result,
        }

    except Exception as e:
        logger.error(f"ILE feedback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) or repr(e))