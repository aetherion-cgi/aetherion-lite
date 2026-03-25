"""
ILE Anomaly Detection Core

Generic anomaly detection engine using statistical profiling.
Maintains per-tenant/per-function behavior profiles and detects deviations.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector:
    """
    Generic anomaly detection using statistical profiling.
    
    Maintains running statistics (mean, std) for feature vectors
    and scores deviations using z-scores and isolation.
    """
    
    def __init__(self, db_manager=None, redis_client=None):
        """
        Initialize anomaly detector.
        
        Args:
            db_manager: Database manager for persistent storage
            redis_client: Redis client for fast access
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        
        # Profiles: {profile_key: {feature: {mean, var, count}}}
        self.profiles: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {'mean': 0.0, 'var': 1.0, 'count': 0})
        )
        
        # Anomaly detection parameters
        self.z_score_threshold = 3.0  # Standard deviations for anomaly
        self.min_samples = 10  # Minimum samples before anomaly detection
        
        logger.info("Anomaly Detector initialized")
    
    def _profile_key(
        self,
        tenant_id: Optional[str] = None,
        function_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Create profile key from context.
        
        Args:
            tenant_id: Tenant identifier
            function_name: Function name
            context: Additional context
        
        Returns:
            Profile key string
        """
        parts = []
        
        if tenant_id:
            parts.append(f"tenant:{tenant_id}")
        if function_name:
            parts.append(f"fn:{function_name}")
        if context:
            sorted_context = sorted(context.items())
            parts.append(f"ctx:{json.dumps(sorted_context)}")
        
        return "|".join(parts) if parts else "global"
    
    async def update_profile(
        self,
        features: Dict[str, float],
        tenant_id: Optional[str] = None,
        function_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> None:
        """
        Update statistical profile with new feature vector.
        Uses Welford's online algorithm for running mean and variance.
        
        Args:
            features: Dictionary of feature name -> value
            tenant_id: Optional tenant identifier
            function_name: Optional function name
            context: Optional context dictionary
        """
        profile_key = self._profile_key(tenant_id, function_name, context)
        profile = self.profiles[profile_key]
        
        for feature_name, value in features.items():
            stats = profile[feature_name]
            
            # Welford's online algorithm for mean and variance
            count = stats['count']
            old_mean = stats['mean']
            
            # Update count
            count += 1
            
            # Update mean
            delta = value - old_mean
            new_mean = old_mean + delta / count
            
            # Update variance
            delta2 = value - new_mean
            new_var = stats['var'] + (delta * delta2 - stats['var']) / count
            
            # Store updated statistics
            stats['mean'] = new_mean
            stats['var'] = max(new_var, 1e-6)  # Avoid zero variance
            stats['count'] = count
        
        # Persist to storage
        await self._persist_profile(profile_key)
        
        logger.debug(f"Updated profile: {profile_key}, features: {list(features.keys())}")
    
    async def score(
        self,
        features: Dict[str, float],
        tenant_id: Optional[str] = None,
        function_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> float:
        """
        Score feature vector for anomaly.
        Returns anomaly score where higher = more anomalous.
        
        Args:
            features: Dictionary of feature name -> value
            tenant_id: Optional tenant identifier
            function_name: Optional function name
            context: Optional context dictionary
        
        Returns:
            Anomaly score (0.0 = normal, 1.0+ = anomalous)
        """
        profile_key = self._profile_key(tenant_id, function_name, context)
        
        # Load profile if needed
        await self._load_profile_if_needed(profile_key)
        
        profile = self.profiles[profile_key]
        
        # Check if we have enough samples
        sample_counts = [
            stats['count'] for stats in profile.values()
            if stats['count'] > 0
        ]
        
        if not sample_counts or max(sample_counts) < self.min_samples:
            # Not enough data, cannot determine anomaly
            return 0.0
        
        # Calculate z-scores for each feature
        z_scores = []
        
        for feature_name, value in features.items():
            if feature_name not in profile:
                # Unknown feature, slightly suspicious
                z_scores.append(1.0)
                continue
            
            stats = profile[feature_name]
            
            if stats['count'] < self.min_samples:
                # Not enough samples for this feature
                continue
            
            # Calculate z-score
            mean = stats['mean']
            std = np.sqrt(stats['var'])
            
            if std > 0:
                z_score = abs(value - mean) / std
                z_scores.append(z_score)
        
        if not z_scores:
            return 0.0
        
        # Anomaly score = max z-score (most anomalous feature)
        max_z_score = max(z_scores)
        
        # Normalize to [0, 1] scale
        # z > 3 => score > 1.0 (definite anomaly)
        anomaly_score = max_z_score / self.z_score_threshold
        
        logger.debug(
            f"Anomaly score for {profile_key}: {anomaly_score:.2f} "
            f"(max z-score: {max_z_score:.2f})"
        )
        
        return anomaly_score
    
    async def is_anomaly(
        self,
        features: Dict[str, float],
        tenant_id: Optional[str] = None,
        function_name: Optional[str] = None,
        context: Optional[Dict] = None,
        threshold: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Check if feature vector is anomalous.
        
        Args:
            features: Feature vector
            tenant_id: Optional tenant identifier
            function_name: Optional function name
            context: Optional context dictionary
            threshold: Custom anomaly threshold (default: 1.0)
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if threshold is None:
            threshold = 1.0
        
        score = await self.score(features, tenant_id, function_name, context)
        is_anom = score >= threshold
        
        return is_anom, score
    
    async def get_profile_stats(
        self,
        tenant_id: Optional[str] = None,
        function_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get current profile statistics.
        
        Args:
            tenant_id: Optional tenant identifier
            function_name: Optional function name
            context: Optional context dictionary
        
        Returns:
            Dictionary of feature statistics
        """
        profile_key = self._profile_key(tenant_id, function_name, context)
        await self._load_profile_if_needed(profile_key)
        
        profile = self.profiles[profile_key]
        
        # Convert to readable format
        stats = {}
        for feature_name, feature_stats in profile.items():
            stats[feature_name] = {
                'mean': feature_stats['mean'],
                'std': np.sqrt(feature_stats['var']),
                'count': feature_stats['count']
            }
        
        return stats
    
    async def _persist_profile(self, profile_key: str) -> None:
        """Persist profile to Redis/Postgres if available"""
        if not self.redis_client:
            return
        
        try:
            profile = self.profiles[profile_key]
            
            # Store in Redis with TTL
            redis_key = f"anomaly:profile:{profile_key}"
            await self.redis_client.setex(
                redis_key,
                86400,  # 24 hour TTL
                json.dumps({
                    feature: {
                        'mean': stats['mean'],
                        'var': stats['var'],
                        'count': stats['count']
                    }
                    for feature, stats in profile.items()
                })
            )
        except Exception as e:
            logger.error(f"Error persisting anomaly profile: {e}")
    
    async def _load_profile_if_needed(self, profile_key: str) -> None:
        """Load profile from Redis if not in memory"""
        if profile_key in self.profiles and self.profiles[profile_key]:
            return
        
        if not self.redis_client:
            return
        
        try:
            redis_key = f"anomaly:profile:{profile_key}"
            profile_json = await self.redis_client.get(redis_key)
            
            if profile_json:
                profile_data = json.loads(profile_json)
                
                for feature, stats in profile_data.items():
                    self.profiles[profile_key][feature] = stats
        except Exception as e:
            logger.error(f"Error loading anomaly profile: {e}")


# ============================================================================
# TIME-SERIES ANOMALY DETECTOR
# ============================================================================

class TimeSeriesAnomalyDetector:
    """
    Anomaly detector specialized for time-series data.
    Detects spikes, drops, and trend changes.
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize time-series detector.
        
        Args:
            window_size: Size of sliding window for statistics
        """
        self.window_size = window_size
        
        # Time series windows: {series_key: [values]}
        self.windows: Dict[str, List[float]] = defaultdict(list)
    
    def add_value(self, series_key: str, value: float) -> None:
        """Add value to time series"""
        window = self.windows[series_key]
        window.append(value)
        
        # Keep only last window_size values
        if len(window) > self.window_size:
            window.pop(0)
    
    def detect_spike(
        self,
        series_key: str,
        value: float,
        threshold_sigmas: float = 3.0
    ) -> Tuple[bool, float]:
        """
        Detect if value is a spike.
        
        Args:
            series_key: Time series identifier
            value: New value
            threshold_sigmas: Number of standard deviations for spike
        
        Returns:
            Tuple of (is_spike, z_score)
        """
        window = self.windows[series_key]
        
        if len(window) < 10:
            # Not enough history
            return False, 0.0
        
        # Calculate statistics from window
        mean = np.mean(window)
        std = np.std(window)
        
        if std == 0:
            return False, 0.0
        
        # Calculate z-score
        z_score = abs(value - mean) / std
        
        is_spike = z_score > threshold_sigmas
        
        return is_spike, z_score
    
    def detect_trend_change(
        self,
        series_key: str,
        value: float
    ) -> Tuple[bool, str]:
        """
        Detect significant trend changes.
        
        Args:
            series_key: Time series identifier
            value: New value
        
        Returns:
            Tuple of (trend_changed, direction)
        """
        window = self.windows[series_key]
        
        if len(window) < 20:
            return False, "unknown"
        
        # Split into old and recent halves
        mid = len(window) // 2
        old_half = window[:mid]
        recent_half = window[mid:]
        
        old_mean = np.mean(old_half)
        recent_mean = np.mean(recent_half)
        
        # Check for significant change (>20%)
        if old_mean == 0:
            return False, "unknown"
        
        change_pct = abs(recent_mean - old_mean) / old_mean
        
        if change_pct > 0.2:
            direction = "up" if recent_mean > old_mean else "down"
            return True, direction
        
        return False, "stable"


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        detector = AnomalyDetector()
        
        # Simulate normal behavior
        print("Training profile with normal data...")
        for i in range(100):
            features = {
                "request_rate": 50 + np.random.normal(0, 5),
                "response_time": 100 + np.random.normal(0, 10),
                "error_rate": 0.01 + np.random.normal(0, 0.005)
            }
            
            await detector.update_profile(
                features,
                tenant_id="tenant_1",
                function_name="api_call"
            )
        
        # Check profile stats
        stats = await detector.get_profile_stats(
            tenant_id="tenant_1",
            function_name="api_call"
        )
        print(f"\nProfile statistics: {stats}")
        
        # Test normal request
        normal_features = {
            "request_rate": 52,
            "response_time": 105,
            "error_rate": 0.012
        }
        
        is_anom, score = await detector.is_anomaly(
            normal_features,
            tenant_id="tenant_1",
            function_name="api_call"
        )
        print(f"\nNormal request - Anomaly: {is_anom}, Score: {score:.2f}")
        
        # Test anomalous request (spike in error rate)
        anomalous_features = {
            "request_rate": 48,
            "response_time": 102,
            "error_rate": 0.15  # Very high error rate!
        }
        
        is_anom, score = await detector.is_anomaly(
            anomalous_features,
            tenant_id="tenant_1",
            function_name="api_call"
        )
        print(f"Anomalous request - Anomaly: {is_anom}, Score: {score:.2f}")
        
        # Test time-series detector
        print("\n--- Testing Time-Series Detector ---")
        ts_detector = TimeSeriesAnomalyDetector(window_size=50)
        
        # Add normal values
        for i in range(60):
            value = 100 + np.random.normal(0, 5)
            ts_detector.add_value("metric_1", value)
        
        # Test normal value
        is_spike, z = ts_detector.detect_spike("metric_1", 105)
        print(f"Normal value - Spike: {is_spike}, Z-score: {z:.2f}")
        
        # Test spike
        is_spike, z = ts_detector.detect_spike("metric_1", 150)
        print(f"Spike value - Spike: {is_spike}, Z-score: {z:.2f}")
        
        # Test trend detection
        for i in range(30):
            value = 150 + i * 2  # Upward trend
            ts_detector.add_value("metric_2", value)
        
        trend_changed, direction = ts_detector.detect_trend_change("metric_2", 200)
        print(f"Trend change - Changed: {trend_changed}, Direction: {direction}")
        
        print("\n✅ Anomaly Detection test completed!")
    
    asyncio.run(test())
