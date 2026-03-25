'''Domain 7: Security Learner'''
import logging

logger = logging.getLogger(__name__)

class SecurityLearner:
    def __init__(self, validator, registry):
        self.validator = validator
        self.registry = registry
        logger.info("Security Learner initialized")
    
    async def propose_security_updates(self, anomalies: List[Dict]) -> List[Dict]:
        '''Propose security threshold updates based on anomalies'''
        proposals = []
        
        # Analyze anomaly patterns
        high_severity = [a for a in anomalies if a.get("severity") in ["high", "critical"]]
        
        if len(high_severity) > 10:
            # Propose stricter thresholds
            proposals.append({
                "api": "function_broker",
                "key": "security_threshold",
                "old_value": 0.8,
                "new_value": 0.7,  # Stricter
                "reason": f"High anomaly rate: {len(high_severity)} critical events"
            })
        
        logger.info(f"Proposed {len(proposals)} security updates")
        return proposals
    
    async def apply_security_updates(self, proposals: List[Dict]) -> None:
        '''Apply approved security updates'''
        from ...models import LearningEvent, DomainType, LearningEventType, APIType
        
        for proposal in proposals:
            event = LearningEvent(
                event_type=LearningEventType.SECURITY,
                domain=DomainType.SECURITY,
                api=APIType.BUE,  # Or relevant API
                inputs={"proposal": proposal},
                predicted={"new_threshold": proposal["new_value"]}
            )
            
            validation = await self.validator.validate_learning(event)
            
            if validation.decision.value == "approved":
                await self.registry.update_config(
                    proposal["api"],
                    proposal["key"],
                    proposal["new_value"],
                    metadata={"reason": proposal["reason"], "source": "security_learning"}
                )
                logger.info(f"Applied security update: {proposal['key']}")
