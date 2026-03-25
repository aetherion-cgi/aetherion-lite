'''Domain 5: Federated Client Template'''
import logging

logger = logging.getLogger(__name__)

class FederatedClient:
    '''Template for edge device learning'''
    def __init__(self, client_id: str):
        self.client_id = client_id
        logger.info(f"Federated Client {client_id} initialized")
    
    async def compute_local_update(self, local_data: List) -> Dict:
        '''Compute model update from local data'''
        # Simplified: count statistics
        update = {
            "client_id": self.client_id,
            "samples": len(local_data),
            "avg_signal": sum(d.get("signal", 0) for d in local_data) / len(local_data) if local_data else 0,
            "gradient": {}  # Would contain actual gradients
        }
        
        logger.debug(f"Computed local update: {update}")
        return update
    
    async def send_update(self, update: Dict) -> None:
        '''Send update to central server'''
        # Would send via network in production
        logger.info(f"Sent update from client {self.client_id}")
