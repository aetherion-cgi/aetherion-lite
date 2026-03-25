'''Domain 7: Security Anomaly Detector'''
import logging

logger = logging.getLogger(__name__)

class SecurityAnomalyDetector:
    def __init__(self, anomaly_core):
        self.anomaly_core = anomaly_core
        logger.info("Security Anomaly Detector initialized")
    
    async def detect(self, features: Dict, tenant_id: str, function_name: str) -> tuple:
        '''Detect security anomalies'''
        is_anomaly, score = await self.anomaly_core.is_anomaly(
            features=features,
            tenant_id=tenant_id,
            function_name=function_name,
            threshold=0.8  # Lower threshold for security
        )
        
        logger.info(f"Security anomaly check: {is_anomaly}, score={score:.2f}")
        return is_anomaly, score
