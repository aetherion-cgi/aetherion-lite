'''Domain 6: Ensemble Coordinator'''
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class EnsembleCoordinator:
    def __init__(self, rl_engine):
        self.rl_engine = rl_engine
        self.performance_data = defaultdict(list)
        logger.info("Ensemble Coordinator initialized")
    
    async def track_performance(self, event: "LearningEvent") -> None:
        '''Track LLM performance from user interactions'''
        if not event.predicted:
            return
        
        model_used = event.predicted.get("model_used", "unknown")
        
        # Extract performance metrics
        perf = {
            "model": model_used,
            "success": event.actual.get("user_satisfied", False) if event.actual else False,
            "response_time": event.metadata.get("response_time_ms", 0),
            "cost": self._estimate_cost(model_used, event.metadata.get("tokens_used", 0))
        }
        
        self.performance_data[model_used].append(perf)
        
        # Update RL engine
        context = {
            "task_type": event.inputs.get("task_type", "general"),
            "complexity": event.inputs.get("complexity", "medium")
        }
        
        # Calculate reward: balance accuracy, cost, latency
        reward = (
            0.6 * float(perf["success"]) +
            0.2 * (1.0 - min(perf["response_time"] / 5000, 1.0)) +  # Normalize latency
            0.2 * (1.0 - min(perf["cost"] / 0.01, 1.0))  # Normalize cost
        )
        
        await self.rl_engine.update(context, model_used, reward)
        
        logger.debug(f"Tracked performance: {model_used}, reward={reward:.2f}")
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        '''Estimate cost based on model and tokens'''
        cost_per_1k = {
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.001
        }
        
        base_cost = cost_per_1k.get(model, 0.005)
        return (tokens / 1000) * base_cost
    
    async def get_routing_weights(self) -> Dict[str, float]:
        '''Get current LLM routing weights'''
        models = ["claude-3-opus", "claude-3-sonnet", "gpt-4", "gpt-3.5-turbo"]
        
        context = {"task_type": "general"}
        scores = await self.rl_engine.get_action_scores(context, models)
        
        # Normalize to weights
        total = sum(scores.values())
        weights = {model: score / total for model, score in scores.items()} if total > 0 else {}
        
        logger.info(f"Current LLM weights: {weights}")
        return weights
