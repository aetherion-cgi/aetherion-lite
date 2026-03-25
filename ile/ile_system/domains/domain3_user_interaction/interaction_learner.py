'''Domain 3: Interaction Learners'''
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class InteractionLearner:
    '''Base class for interaction learning'''
    def __init__(self, api_name: str, db_manager):
        self.api_name = api_name
        self.db = db_manager
        logger.info(f"{api_name} Interaction Learner initialized")
    
    async def process_interaction(self, interaction: "UserInteraction") -> None:
        '''Process user interaction'''
        # Store interaction with embeddings
        features = self._extract_features(interaction)
        
        # Log to database
        logger.debug(f"Processed {self.api_name} interaction: {features}")
    
    def _extract_features(self, interaction: "UserInteraction") -> Dict:
        return {
            "response_time": 500,
            "success": interaction.user_satisfied,
            "task_type": interaction.interaction_type
        }

class UDOALearner(InteractionLearner):
    def __init__(self, db_manager):
        super().__init__("UDOA", db_manager)

class UIELearner(InteractionLearner):
    def __init__(self, db_manager):
        super().__init__("UIE", db_manager)

class CEOALearner(InteractionLearner):
    def __init__(self, db_manager):
        super().__init__("CEOA", db_manager)
