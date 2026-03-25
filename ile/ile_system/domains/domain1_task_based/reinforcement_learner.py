"""
Domain 1: Task-Based Learning - Reinforcement Learner

Computes metrics from learning events and updates RL policies
for adaptive decision-making across all APIs.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# REINFORCEMENT LEARNER
# ============================================================================

class ReinforcementLearner:
    """
    Reinforcement learning for task-based adaptation.
    
    Responsibilities:
    - Compute performance metrics from outcomes
    - Update contextual bandit policies
    - Maintain separate policies per (API, task_type, context)
    """
    
    def __init__(self, rl_engine, metrics_module):
        """
        Initialize reinforcement learner.
        
        Args:
            rl_engine: RLEngine instance for bandit learning
            metrics_module: Metrics computation module
        """
        self.rl_engine = rl_engine
        self.metrics = metrics_module
        logger.info("Reinforcement Learner initialized")
    
    async def compute_metrics(
        self,
        events: List["LearningEvent"]
    ) -> "LearningMetrics":
        """
        Compute comprehensive metrics from learning events.
        
        Args:
            events: List of learning events with outcomes
        
        Returns:
            LearningMetrics object
        """
        from ..models import LearningMetrics, DomainType
        
        if not events:
            return LearningMetrics(
                domain=DomainType.TASK_BASED,
                timeframe_minutes=60,
                total_events=0,
                processed_events=0,
                rejected_events=0,
                approval_rate=1.0,
                avg_benefit_score=0.0,
                avg_harm_score=0.0,
                avg_processing_time_ms=0.0,
                knowledge_items_added=0,
                patterns_discovered=0
            )
        
        # Convert events to format for metrics computation
        event_dicts = []
        for event in events:
            event_dict = {
                "predicted": event.predicted or {},
                "actual": event.actual or {},
                "learning_signal": event.learning_signal
            }
            event_dicts.append(event_dict)
        
        # Compute metrics based on task type
        # For BUE/URPE: probability calibration metrics
        computed = self.metrics.compute_metrics_from_events(
            event_dicts,
            metric_type="probability"
        )
        
        # Extract learning signal statistics
        signals = [e.learning_signal for e in events if e.learning_signal is not None]
        signal_stats = self.metrics.analyze_learning_signals(signals) if signals else {}
        
        # Create metrics object
        metrics_obj = LearningMetrics(
            domain=DomainType.TASK_BASED,
            api=events[0].api if events else None,
            timeframe_minutes=60,
            total_events=len(events),
            processed_events=len(events),
            rejected_events=0,
            approval_rate=1.0,
            avg_benefit_score=max(0.0, signal_stats.get('mean', 0.0) * 50 + 50),
            avg_harm_score=max(0.0, -signal_stats.get('mean', 0.0) * 50 + 50),
            avg_processing_time_ms=0.0,
            knowledge_items_added=0,
            patterns_discovered=0
        )
        
        logger.info(
            f"Computed metrics: {len(events)} events, "
            f"avg_signal={signal_stats.get('mean', 0.0):.2f}"
        )
        
        return metrics_obj
    
    async def update_policy(
        self,
        events: List["LearningEvent"]
    ) -> Dict[str, int]:
        """
        Update RL policies based on learning events.
        
        Args:
            events: List of learning events with outcomes
        
        Returns:
            Dictionary with update statistics
        """
        updates = {"total": 0, "by_api": {}, "by_context": {}}
        
        for event in events:
            if event.learning_signal is None:
                continue
            
            # Extract context from event
            context = self._extract_context(event)
            
            # Extract action (what decision was made)
            action = self._extract_action(event)
            
            # Update RL engine
            await self.rl_engine.update(
                context=context,
                action=action,
                reward=event.learning_signal
            )
            
            updates["total"] += 1
            updates["by_api"][event.api.value] = updates["by_api"].get(event.api.value, 0) + 1
            
            context_key = self._context_to_key(context)
            updates["by_context"][context_key] = updates["by_context"].get(context_key, 0) + 1
        
        logger.info(
            f"Updated RL policies: {updates['total']} updates across "
            f"{len(updates['by_api'])} APIs and {len(updates['by_context'])} contexts"
        )
        
        return updates
    
    def _extract_context(self, event: "LearningEvent") -> Dict:
        """
        Extract context features from learning event.
        
        Args:
            event: Learning event
        
        Returns:
            Context dictionary for RL
        """
        context = {
            "api": event.api.value,
            "domain": event.domain.value
        }
        
        # Add task-specific context from inputs
        if event.inputs:
            # For BUE: industry, company size, etc.
            if "industry" in event.inputs:
                context["industry"] = event.inputs["industry"]
            
            if "company_size" in event.inputs:
                context["company_size"] = event.inputs["company_size"]
            
            # For URPE: scenario type, risk level
            if "scenario_type" in event.inputs:
                context["scenario_type"] = event.inputs["scenario_type"]
            
            if "complexity" in event.inputs:
                context["complexity"] = event.inputs["complexity"]
        
        return context
    
    def _extract_action(self, event: "LearningEvent") -> str:
        """
        Extract action (decision made) from event.
        
        Args:
            event: Learning event
        
        Returns:
            Action string
        """
        if not event.predicted:
            return "default"
        
        # For BUE: risk tier classification
        if event.api.value == "bue":
            risk_score = event.predicted.get("risk_score", 0.5)
            
            if risk_score < 0.2:
                return "low_risk"
            elif risk_score < 0.5:
                return "medium_risk"
            else:
                return "high_risk"
        
        # For URPE: recommended action
        if event.api.value == "urpe":
            return event.predicted.get("recommended_action", "default")
        
        # For UIE: model selection
        if event.api.value == "uie":
            return event.predicted.get("model_used", "default")
        
        return "default"
    
    def _context_to_key(self, context: Dict) -> str:
        """Convert context dict to string key"""
        items = sorted(context.items())
        return "|".join(f"{k}:{v}" for k, v in items)
    
    async def get_best_action(
        self,
        api: str,
        inputs: Dict,
        candidate_actions: Optional[List[str]] = None
    ) -> str:
        """
        Get best action for given inputs using current policy.
        
        Args:
            api: API identifier
            inputs: Input features
            candidate_actions: List of possible actions
        
        Returns:
            Recommended action
        """
        # Create context from inputs
        from ..models import APIType, DomainType, LearningEvent
        
        dummy_event = LearningEvent(
            event_type="outcome",
            domain=DomainType.TASK_BASED,
            api=APIType(api),
            inputs=inputs,
            predicted=None,
            actual=None
        )
        
        context = self._extract_context(dummy_event)
        
        # Get best action from RL engine
        if candidate_actions is None:
            # Default candidates based on API
            if api == "bue":
                candidate_actions = ["low_risk", "medium_risk", "high_risk"]
            elif api == "uie":
                candidate_actions = ["claude-3-opus", "claude-3-sonnet", "gpt-4"]
            else:
                candidate_actions = ["default"]
        
        best_action = await self.rl_engine.best_action(
            context=context,
            candidate_actions=candidate_actions
        )
        
        logger.debug(
            f"Best action for {api} with context {context}: {best_action}"
        )
        
        return best_action
    
    async def get_action_scores(
        self,
        api: str,
        inputs: Dict,
        candidate_actions: List[str]
    ) -> Dict[str, float]:
        """
        Get expected reward scores for all candidate actions.
        
        Args:
            api: API identifier
            inputs: Input features
            candidate_actions: List of possible actions
        
        Returns:
            Dictionary mapping actions to expected rewards
        """
        from ..models import APIType, DomainType, LearningEvent
        
        dummy_event = LearningEvent(
            event_type="outcome",
            domain=DomainType.TASK_BASED,
            api=APIType(api),
            inputs=inputs,
            predicted=None,
            actual=None
        )
        
        context = self._extract_context(dummy_event)
        
        scores = await self.rl_engine.get_action_scores(
            context=context,
            candidate_actions=candidate_actions
        )
        
        return scores
    
    async def export_policy_snapshot(self) -> Dict:
        """
        Export complete RL policy for backup/analysis.
        
        Returns:
            Policy dictionary
        """
        policy = await self.rl_engine.export_policy()
        
        logger.info("Exported RL policy snapshot")
        
        return policy


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Reinforcement Learner - requires RL engine and metrics module")
    print("See integration tests for full testing")
