'''Domain 2: Knowledge Integrator'''
import logging
from typing import List

logger = logging.getLogger(__name__)

class KnowledgeIntegrator:
    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph
        logger.info("Knowledge Integrator initialized")
    
    async def integrate(self, knowledge_items: List["KnowledgeItem"]) -> Dict:
        '''Integrate knowledge into knowledge graph'''
        added = 0
        
        for item in knowledge_items:
            try:
                # Store in knowledge graph
                node_id = await self.kg.store_knowledge(item)
                added += 1
            except Exception as e:
                logger.error(f"Error integrating knowledge: {e}")
        
        logger.info(f"Integrated {added} knowledge items into graph")
        return {"added": added, "total": len(knowledge_items)}
