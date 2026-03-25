'''Domain 4: Relevance Mapper'''
import logging

logger = logging.getLogger(__name__)

class RelevanceMapper:
    def __init__(self):
        logger.info("Relevance Mapper initialized")
    
    def map_relevance(self, patterns: List["CrossDomainPattern"]) -> Dict:
        '''Map patterns to relevant APIs/domains'''
        relevance_map = {}
        
        for pattern in patterns:
            for api in pattern.applicable_apis:
                if api.value not in relevance_map:
                    relevance_map[api.value] = []
                
                relevance_map[api.value].append({
                    "pattern_id": str(pattern.pattern_id),
                    "pattern_name": pattern.pattern_name,
                    "relevance_score": pattern.accuracy
                })
        
        logger.info(f"Mapped {len(patterns)} patterns to {len(relevance_map)} APIs")
        return relevance_map
