"""
Domain 1: Task-Based Learning - Task Outcome Tracker

Stores predictions and outcomes from all APIs, matches them together,
and generates learning events for reinforcement learning.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ============================================================================
# TASK OUTCOME TRACKER
# ============================================================================

class TaskOutcomeTracker:
    """
    Tracks predictions and outcomes for task-based learning.
    
    Responsibilities:
    - Store predictions with unique IDs
    - Match outcomes to predictions
    - Generate learning events when outcome arrives
    - Handle delayed feedback (days/weeks later)
    """
    
    def __init__(self, db_manager):
        """
        Initialize task outcome tracker.
        
        Args:
            db_manager: Database manager for storage
        """
        self.db_manager = db_manager
        logger.info("Task Outcome Tracker initialized")
    
    async def record_prediction(self, event: "LearningEvent") -> None:
        """
        Record a prediction for future outcome matching.
        
        Args:
            event: Learning event with prediction
        """
        from ..models import TaskOutcome
        
        # Create task outcome record
        outcome = TaskOutcome(
            prediction_id=event.prediction_id or str(event.event_id),
            api=event.api,
            predicted_at=event.timestamp,
            inputs=event.inputs,
            predicted=event.predicted or {},
            confidence=event.predicted.get("confidence") if event.predicted else None,
            actual=None,  # Will be filled when outcome arrives
            processed=False
        )
        
        # Store in database
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import insert
                from ..database import TaskOutcomeTable
                
                await session.execute(
                    insert(TaskOutcomeTable).values(
                        outcome_id=str(outcome.outcome_id),
                        prediction_id=outcome.prediction_id,
                        api=outcome.api.value,
                        predicted_at=outcome.predicted_at,
                        inputs=outcome.inputs,
                        predicted=outcome.predicted,
                        confidence=outcome.confidence,
                        processed=outcome.processed
                    )
                )
                await session.commit()
            
            logger.info(
                f"Recorded prediction: {outcome.prediction_id} "
                f"from {outcome.api}"
            )
        
        except Exception as e:
            logger.error(f"Error recording prediction: {e}")
    
    async def record_outcome(
        self,
        prediction_id: str,
        actual: Dict,
        outcome_date: Optional[datetime] = None
    ) -> Optional["LearningEvent"]:
        """
        Record actual outcome and match to prediction.
        
        Args:
            prediction_id: ID of original prediction
            actual: Actual outcome data
            outcome_date: Date of outcome (for delayed feedback)
        
        Returns:
            Learning event if match found, None otherwise
        """
        from ..models import LearningEvent, LearningEventType, DomainType
        from ..models import calculate_learning_signal
        
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import select, update
                from ..database import TaskOutcomeTable
                
                # Find prediction
                result = await session.execute(
                    select(TaskOutcomeTable).where(
                        TaskOutcomeTable.prediction_id == prediction_id
                    )
                )
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"No prediction found for ID: {prediction_id}")
                    return None
                
                # Calculate delay
                predicted_at = row.predicted_at
                actual_at = outcome_date or datetime.utcnow()
                delay_days = (actual_at - predicted_at).days
                
                # Calculate learning signal
                predicted = row.predicted
                api = row.api
                
                learning_signal = calculate_learning_signal(
                    predicted,
                    actual,
                    api
                )
                
                # Update outcome record
                await session.execute(
                    update(TaskOutcomeTable).where(
                        TaskOutcomeTable.prediction_id == prediction_id
                    ).values(
                        actual=actual,
                        actual_at=actual_at,
                        outcome_delay_days=delay_days,
                        learning_signal=learning_signal,
                        processed=False  # Will be processed by RL
                    )
                )
                await session.commit()
                
                # Create learning event
                event = LearningEvent(
                    event_type=LearningEventType.OUTCOME,
                    domain=DomainType.TASK_BASED,
                    api=api,
                    prediction_id=prediction_id,
                    inputs=row.inputs,
                    predicted=predicted,
                    actual=actual,
                    learning_signal=learning_signal,
                    metadata={
                        "outcome_delay_days": delay_days,
                        "predicted_at": predicted_at.isoformat(),
                        "actual_at": actual_at.isoformat()
                    }
                )
                
                logger.info(
                    f"Recorded outcome: {prediction_id}, "
                    f"signal={learning_signal:.2f}, delay={delay_days}d"
                )
                
                return event
        
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
            return None
    
    async def get_recent_learning_events(
        self,
        api: Optional[str] = None,
        limit: int = 1000,
        min_delay_days: int = 0
    ) -> List["LearningEvent"]:
        """
        Get recent learning events with outcomes.
        
        Args:
            api: Optional API filter
            limit: Maximum number of events
            min_delay_days: Minimum outcome delay (for mature outcomes)
        
        Returns:
            List of learning events
        """
        from ..models import LearningEvent, LearningEventType, DomainType
        
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import select, and_
                from ..database import TaskOutcomeTable
                
                # Build query
                query = select(TaskOutcomeTable).where(
                    and_(
                        TaskOutcomeTable.actual.isnot(None),
                        TaskOutcomeTable.outcome_delay_days >= min_delay_days
                    )
                )
                
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                query = query.order_by(
                    TaskOutcomeTable.actual_at.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                # Convert to learning events
                events = []
                for row in rows:
                    event = LearningEvent(
                        event_type=LearningEventType.OUTCOME,
                        domain=DomainType.TASK_BASED,
                        api=row.api,
                        prediction_id=row.prediction_id,
                        inputs=row.inputs,
                        predicted=row.predicted,
                        actual=row.actual,
                        learning_signal=row.learning_signal,
                        metadata={
                            "outcome_delay_days": row.outcome_delay_days,
                            "predicted_at": row.predicted_at.isoformat(),
                            "actual_at": row.actual_at.isoformat()
                        }
                    )
                    events.append(event)
                
                logger.info(f"Retrieved {len(events)} learning events")
                return events
        
        except Exception as e:
            logger.error(f"Error getting learning events: {e}")
            return []
    
    async def mark_processed(
        self,
        prediction_ids: List[str]
    ) -> None:
        """
        Mark outcomes as processed by RL.
        
        Args:
            prediction_ids: List of prediction IDs to mark
        """
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import update
                from ..database import TaskOutcomeTable
                
                await session.execute(
                    update(TaskOutcomeTable).where(
                        TaskOutcomeTable.prediction_id.in_(prediction_ids)
                    ).values(
                        processed=True,
                        processed_at=datetime.utcnow()
                    )
                )
                await session.commit()
            
            logger.info(f"Marked {len(prediction_ids)} outcomes as processed")
        
        except Exception as e:
            logger.error(f"Error marking processed: {e}")
    
    async def get_unprocessed_outcomes(
        self,
        api: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Get outcomes that haven't been processed yet.
        
        Args:
            api: Optional API filter
            limit: Maximum number of outcomes
        
        Returns:
            List of outcome dictionaries
        """
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import select, and_
                from ..database import TaskOutcomeTable
                
                # Build query
                query = select(TaskOutcomeTable).where(
                    and_(
                        TaskOutcomeTable.actual.isnot(None),
                        TaskOutcomeTable.processed == False
                    )
                )
                
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                query = query.order_by(
                    TaskOutcomeTable.actual_at.asc()
                ).limit(limit)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                outcomes = [
                    {
                        "prediction_id": row.prediction_id,
                        "api": row.api,
                        "inputs": row.inputs,
                        "predicted": row.predicted,
                        "actual": row.actual,
                        "learning_signal": row.learning_signal,
                        "delay_days": row.outcome_delay_days
                    }
                    for row in rows
                ]
                
                logger.info(f"Found {len(outcomes)} unprocessed outcomes")
                return outcomes
        
        except Exception as e:
            logger.error(f"Error getting unprocessed outcomes: {e}")
            return []
    
    async def get_statistics(
        self,
        api: Optional[str] = None
    ) -> Dict:
        """
        Get statistics about predictions and outcomes.
        
        Args:
            api: Optional API filter
        
        Returns:
            Statistics dictionary
        """
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import select, func
                from ..database import TaskOutcomeTable
                
                # Total predictions
                query = select(func.count(TaskOutcomeTable.prediction_id))
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                result = await session.execute(query)
                total_predictions = result.scalar() or 0
                
                # Predictions with outcomes
                query = select(func.count(TaskOutcomeTable.prediction_id)).where(
                    TaskOutcomeTable.actual.isnot(None)
                )
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                result = await session.execute(query)
                with_outcomes = result.scalar() or 0
                
                # Average learning signal
                query = select(func.avg(TaskOutcomeTable.learning_signal)).where(
                    TaskOutcomeTable.learning_signal.isnot(None)
                )
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                result = await session.execute(query)
                avg_signal = result.scalar() or 0.0
                
                # Average delay
                query = select(func.avg(TaskOutcomeTable.outcome_delay_days)).where(
                    TaskOutcomeTable.outcome_delay_days.isnot(None)
                )
                if api:
                    query = query.where(TaskOutcomeTable.api == api)
                
                result = await session.execute(query)
                avg_delay = result.scalar() or 0.0
                
                stats = {
                    "total_predictions": total_predictions,
                    "predictions_with_outcomes": with_outcomes,
                    "match_rate": with_outcomes / total_predictions if total_predictions > 0 else 0,
                    "avg_learning_signal": float(avg_signal),
                    "avg_outcome_delay_days": float(avg_delay)
                }
                
                return stats
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Task Outcome Tracker - requires database connection for testing")
    print("See integration tests for full testing")
