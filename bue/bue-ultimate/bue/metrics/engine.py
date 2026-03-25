"""Metrics Engine - Core metric computation"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MetricEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        logger.info("MetricEngine initialized")
    
    def compute_metrics(self, data: Dict[str, Any], metric_definitions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return data
    
    def normalize_metric(self, value: float, metric_type: str, industry: str) -> float:
        ranges = {
            'saas': {'arr_growth': (0, 200), 'ltv_cac': (0, 10), 'churn_rate': (0.10, 0)},
            'cre': {'cap_rate': (0, 0.15), 'dscr': (0, 3), 'occupancy': (0, 1)}
        }
        
        if industry not in ranges or metric_type not in ranges[industry]:
            return value
        
        min_val, max_val = ranges[industry][metric_type]
        
        if min_val > max_val:
            normalized = 100 * (1 - (value - max_val) / (min_val - max_val))
        else:
            normalized = 100 * (value - min_val) / (max_val - min_val)
        
        return max(0, min(100, normalized))
