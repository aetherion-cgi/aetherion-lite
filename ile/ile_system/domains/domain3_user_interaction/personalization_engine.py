'''Domain 3: Personalization Engine'''
import logging

logger = logging.getLogger(__name__)

class PersonalizationEngine:
    def __init__(self, validator):
        self.validator = validator
        logger.info("Personalization Engine initialized")
    
    async def build_policies(self, patterns: List[Dict]) -> List[Dict]:
        '''Build personalization policies from patterns'''
        from ...models import LearningEvent, DomainType, LearningEventType, APIType
        
        policies = []
        
        for pattern in patterns:
            if pattern["success_rate"] > 0.8:
                policy = {
                    "segment": pattern["task_type"],
                    "tone": "professional",
                    "verbosity": "concise",
                    "explanation_depth": "moderate"
                }
                
                # Validate through governance
                event = LearningEvent(
                    event_type=LearningEventType.UPDATE,
                    domain=DomainType.USER_INTERACTION,
                    api=APIType.UIE,
                    inputs={"pattern": pattern},
                    predicted={"policy": policy}
                )
                
                validation = await self.validator.validate_learning(event)
                
                if validation.decision.value == "approved":
                    policies.append(policy)
        
        logger.info(f"Built {len(policies)} personalization policies")
        return policies
