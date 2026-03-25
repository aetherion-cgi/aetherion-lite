'''Domain 5: Federated Server'''
import logging

logger = logging.getLogger(__name__)

class FederatedServer:
    def __init__(self, validator, registry):
        self.validator = validator
        self.registry = registry
        self.client_updates = []
        logger.info("Federated Server initialized")
    
    async def receive_update(self, update: Dict) -> None:
        '''Receive update from edge client'''
        self.client_updates.append(update)
        logger.debug(f"Received update from client {update.get('client_id')}")
    
    async def aggregate_updates(self) -> Dict:
        '''Aggregate updates using FedAvg'''
        if not self.client_updates:
            return {}
        
        # Simple averaging
        total_samples = sum(u.get("samples", 0) for u in self.client_updates)
        
        aggregated = {
            "num_clients": len(self.client_updates),
            "total_samples": total_samples,
            "avg_signal": sum(
                u.get("avg_signal", 0) * u.get("samples", 0) 
                for u in self.client_updates
            ) / total_samples if total_samples > 0 else 0
        }
        
        # Clear updates
        self.client_updates.clear()
        
        logger.info(f"Aggregated updates from {aggregated['num_clients']} clients")
        return aggregated
    
    async def propose_model_update(self, aggregated: Dict) -> None:
        '''Propose model update from aggregated learning'''
        from ...models import LearningEvent, DomainType, LearningEventType, APIType
        
        event = LearningEvent(
            event_type=LearningEventType.UPDATE,
            domain=DomainType.FEDERATED_EDGE,
            api=APIType.BUE,  # Or whichever API
            inputs={"federated_update": aggregated},
            predicted={"new_params": aggregated}
        )
        
        validation = await self.validator.validate_learning(event)
        
        if validation.decision.value == "approved":
            # Apply update through registry
            await self.registry.update_config(
                "bue",
                "federated_params",
                aggregated,
                metadata={"source": "federated_learning"}
            )
            logger.info("Applied federated model update")
