"""Risk Engine - CPU-based Monte Carlo and risk analysis"""

from typing import Dict, Any, Optional, List
import numpy as np
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskProfile:
    var_95: float
    cvar_95: float
    volatility: float
    downside_risk: float
    upside_potential: float


class RiskEngine:
    """CPU-based risk analysis engine"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        logger.info("RiskEngine initialized (CPU mode)")
    
    async def run_monte_carlo(
        self,
        metrics: Dict[str, Any],
        simulations: int = 10_000,
        confidence_levels: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        import time
        start = time.time()
        
        confidence_levels = confidence_levels or [0.10, 0.25, 0.50, 0.75, 0.90]
        
        base_value = metrics.get('noi') or metrics.get('revenue') or metrics.get('arr', 0)
        volatility = metrics.get('volatility', 0.15)
        growth_rate = metrics.get('growth_rate', 0.0)
        time_horizon = 60
        
        randoms = np.random.randn(simulations)
        
        dt = time_horizon / 12.0
        drift = (growth_rate - 0.5 * volatility ** 2) * dt
        diffusion = volatility * np.sqrt(dt) * randoms
        
        samples = base_value * np.exp(drift + diffusion)
        
        mean = float(np.mean(samples))
        std = float(np.std(samples))
        
        percentiles = {}
        for p in confidence_levels:
            percentiles[f'p{int(p*100)}'] = float(np.percentile(samples, p * 100))
        
        scenarios = {
            'base': mean,
            'upside': float(np.percentile(samples, 75)),
            'downside': float(np.percentile(samples, 25)),
            'best_case': float(np.max(samples)),
            'worst_case': float(np.min(samples))
        }
        
        confidence_intervals = {}
        for conf in [0.90, 0.95, 0.99]:
            alpha = (1 - conf) / 2
            lower = float(np.percentile(samples, alpha * 100))
            upper = float(np.percentile(samples, (1 - alpha) * 100))
            confidence_intervals[conf] = (lower, upper)
        
        var_95 = float(np.percentile(samples, 5))
        worst_5pct = samples[samples <= var_95]
        cvar_95 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else var_95
        
        execution_time_ms = (time.time() - start) * 1000
        
        logger.info(f"CPU Monte Carlo complete - {simulations:,} simulations in {execution_time_ms:.0f}ms")
        
        return {
            'mean': mean,
            'std': std,
            'percentiles': percentiles,
            'scenarios': scenarios,
            'confidence_intervals': confidence_intervals,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'execution_time_ms': execution_time_ms,
            'simulations_run': simulations,
            'gpu_accelerated': False,
            'risk_score': self._calculate_risk_score(samples, mean, std)
        }
    
    def _calculate_risk_score(self, samples: np.ndarray, mean: float, std: float) -> float:
        cv = (std / mean) if mean > 0 else 1.0
        losses = samples[samples < 0]
        prob_loss = len(losses) / len(samples)
        risk_score = min(1.0, (cv * 0.7 + prob_loss * 0.3))
        return risk_score
