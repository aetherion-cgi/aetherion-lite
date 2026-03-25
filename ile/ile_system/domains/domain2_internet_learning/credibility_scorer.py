'''Domain 2: Credibility Scorer'''
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class CredibilityScorer:
    def __init__(self):
        self.domain_scores = {
            ".gov": 0.95,
            ".edu": 0.90,
            ".org": 0.75,
            ".com": 0.60,
        }
        logger.info("Credibility Scorer initialized")
    
    def score_source(self, url: str, source_type: str) -> float:
        '''Score source credibility based on domain and type'''
        score = 0.5  # Default
        
        # Check domain extension
        for ext, ext_score in self.domain_scores.items():
            if ext in url:
                score = ext_score
                break
        
        # Adjust for source type
        if source_type == "academic":
            score += 0.1
        elif source_type == "government":
            score = max(score, 0.9)
        
        return min(1.0, score)
