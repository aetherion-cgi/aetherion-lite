"""
BUE Meta-Learning Module
"""
from typing import Dict, List, Any, Optional
from collections import defaultdict

class MetaLearner:
    """Meta-learning system for BUE Agent"""
    
    def __init__(self):
        self.strategy_performance: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'success_count': 0,
            'total_count': 0,
            'avg_confidence': 0.0
        })
    
    async def record_pattern(self, pattern: Dict[str, Any]) -> None:
        """Record new analysis pattern"""
        query_type = pattern['query_type']
        strategy = pattern.get('strategy', 'unknown')
        confidence = pattern.get('confidence_score', 0.0)
        
        # Update statistics
        stats = self.strategy_performance[f"{query_type}:{strategy}"]
        stats['total_count'] += 1
        if pattern.get('governance_approved', True) and confidence > 0.7:
            stats['success_count'] += 1
        
        # Running average
        n = stats['total_count']
        stats['avg_confidence'] = (stats['avg_confidence'] * (n-1) + confidence) / n
    
    async def get_optimal_strategy(self, query_type: str, industry: str) -> Optional[Dict[str, Any]]:
        """Recommend optimal strategy"""
        best_key = None
        best_score = 0.0
        
        for key, stats in self.strategy_performance.items():
            if query_type in key:
                score = stats['success_count'] / max(stats['total_count'], 1)
                if score > best_score:
                    best_score = score
                    best_key = key
        
        if best_key:
            return {
                'recommended_strategy': best_key.split(':')[1],
                'confidence': best_score,
                'based_on_analyses': self.strategy_performance[best_key]['total_count']
            }
        return None
