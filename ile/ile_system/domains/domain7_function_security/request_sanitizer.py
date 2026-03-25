'''Domain 7: Request Sanitizer'''
import logging

logger = logging.getLogger(__name__)

class RequestSanitizer:
    def __init__(self):
        logger.info("Request Sanitizer initialized")
    
    def extract_features(self, security_event: "SecurityEvent") -> Dict:
        '''Extract features from security event'''
        features = {
            "request_rate": len(security_event.request_pattern.get("recent_requests", [])),
            "error_rate": security_event.request_pattern.get("error_rate", 0.0),
            "unusual_params": len(security_event.request_pattern.get("unusual_params", [])),
            "source_reputation": self._get_ip_reputation(security_event.source_ip)
        }
        
        logger.debug(f"Extracted security features: {features}")
        return features
    
    def _get_ip_reputation(self, ip: str) -> float:
        '''Get reputation score for IP (0.0 = bad, 1.0 = good)'''
        # Simplified: would use actual reputation service
        if ip.startswith("192.168."):
            return 1.0  # Local network
        return 0.7  # Default for external
