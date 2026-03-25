'''
Domain 1: BUE Learning Adapter

Thin adapter for BUE-specific learning events.
'''

import logging
from typing import Dict

logger = logging.getLogger(__name__)

class BUELearningAdapter:
    def __init__(self, tracker):
        self.tracker = tracker
        logger.info("BUE Learning Adapter initialized")
    
    async def process_prediction(self, prediction: Dict) -> None:
        from ...models import LearningEvent, DomainType, LearningEventType, APIType
        
        event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType.TASK_BASED,
            api=APIType.BUE,
            prediction_id=prediction.get("id"),
            inputs=prediction.get("inputs", {}),
            predicted=prediction.get("output", {}),
            metadata=prediction.get("metadata", {})
        )
        
        await self.tracker.record_prediction(event)
        logger.debug(f"Processed BUE prediction: {event.prediction_id}")
    
    async def process_outcome(self, outcome: Dict) -> None:
        prediction_id = outcome.get("prediction_id")
        actual = outcome.get("actual", {})
        
        event = await self.tracker.record_outcome(prediction_id, actual)
        
        if event:
            logger.info(f"Processed BUE outcome: {prediction_id}")
            return event
        return None
