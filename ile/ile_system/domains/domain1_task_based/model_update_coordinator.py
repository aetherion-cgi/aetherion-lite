'''
Domain 1: Model Update Coordinator

Creates learning update proposals and applies approved changes to model registry.
'''

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ModelUpdateCoordinator:
    def __init__(self, model_registry, constitutional_validator):
        self.registry = model_registry
        self.validator = constitutional_validator
        logger.info("Model Update Coordinator initialized")
    
    async def propose_updates(self, metrics: "LearningMetrics") -> List[Dict]:
        proposals = []
        
        # Propose threshold updates based on metrics
        if metrics.avg_benefit_score > 70:
            proposals.append({
                "api": str(metrics.api.value) if metrics.api else "global",
                "key": "risk_threshold",
                "old_value": await self.registry.get_config(str(metrics.api.value), "risk_threshold", 0.5),
                "new_value": 0.45,  # Lower threshold for better performance
                "reason": f"High benefit score: {metrics.avg_benefit_score:.1f}",
                "metrics": metrics.dict()
            })
        
        logger.info(f"Generated {len(proposals)} update proposals")
        return proposals
    
    async def apply_approved_updates(self, proposals: List[Dict]) -> Dict[str, int]:
        from ...models import LearningEvent, DomainType, LearningEventType, APIType
        
        applied = 0
        rejected = 0
        
        for proposal in proposals:
            # Create learning event for validation
            event = LearningEvent(
                event_type=LearningEventType.UPDATE,
                domain=DomainType.TASK_BASED,
                api=APIType(proposal["api"]),
                inputs={"proposal": proposal},
                predicted={"new_value": proposal["new_value"]},
                metadata={"reason": proposal["reason"]}
            )
            
            # Validate through governance
            validation = await self.validator.validate_learning(event)
            
            if validation.decision.value == "approved":
                await self.registry.update_config(
                    proposal["api"],
                    proposal["key"],
                    proposal["new_value"],
                    metadata={"approved_by": "ile", "reason": proposal["reason"]}
                )
                applied += 1
            else:
                rejected += 1
        
        logger.info(f"Applied {applied} updates, rejected {rejected}")
        return {"applied": applied, "rejected": rejected}
