"""
ILE Event Ingestion Service

Ingests learning events from all Aetherion engines (BUE, URPE, UDOA, UIE, CEOA, Function Broker)
and routes them to the ILE orchestrator for processing.

Author: Aetherion Development Team  
Date: November 15, 2025
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# EVENT INGESTION SERVICE
# ============================================================================

class ILEIngestionService:
    """
    Ingests events from all Aetherion engines and routes to orchestrator.
    
    Supports:
    - Kafka-compatible message queues
    - Redis streams
    - Direct API calls
    - WebSocket streams
    """
    
    def __init__(self, orchestrator):
        """
        Initialize ingestion service.
        
        Args:
            orchestrator: ILEOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.running = False
        
        # Topic/queue configurations
        self.topics = {
            "bue.predictions": {"api": "BUE", "priority": 5},
            "bue.outcomes": {"api": "BUE", "priority": 7},
            "urpe.predictions": {"api": "URPE", "priority": 8},
            "urpe.outcomes": {"api": "URPE", "priority": 9},
            "udoa.interactions": {"api": "UDOA", "priority": 5},
            "uie.interactions": {"api": "UIE", "priority": 5},
            "ceoa.decisions": {"api": "CEOA", "priority": 6},
            "function_broker.security": {"api": "FUNCTION_BROKER", "priority": 10},
            "governance.decisions": {"api": "GOVERNANCE", "priority": 9}
        }
        
        # Message processors
        self.consumers: List[asyncio.Task] = []
        
        logger.info("ILE Ingestion Service initialized")
    
    async def start(self):
        """Start ingestion consumers"""
        if self.running:
            logger.warning("Ingestion service already running")
            return
        
        self.running = True
        
        # Start consumers for each topic
        for topic in self.topics.keys():
            consumer = asyncio.create_task(self._consume_topic(topic))
            self.consumers.append(consumer)
        
        logger.info(f"Started {len(self.consumers)} ingestion consumers")
    
    async def stop(self):
        """Stop ingestion service"""
        if not self.running:
            return
        
        logger.info("Stopping ingestion service...")
        self.running = False
        
        # Cancel all consumers
        for consumer in self.consumers:
            consumer.cancel()
        
        # Wait for consumers to finish
        await asyncio.gather(*self.consumers, return_exceptions=True)
        
        self.consumers.clear()
        logger.info("Ingestion service stopped")
    
    async def _consume_topic(self, topic: str):
        """
        Consume messages from a topic.
        
        This is a placeholder that shows the pattern.
        In production, this would connect to actual message queue (Kafka/Redis/etc).
        """
        topic_config = self.topics[topic]
        
        logger.info(f"Consumer started for topic: {topic}")
        
        while self.running:
            try:
                # In production, this would poll from actual queue
                # For now, just sleep to avoid tight loop
                await asyncio.sleep(1)
                
                # Placeholder for actual message consumption
                # message = await queue.consume(topic)
                # await self._process_message(topic, message, topic_config)
                
            except Exception as e:
                logger.error(f"Error consuming from {topic}: {e}")
                await asyncio.sleep(5)  # Backoff on error
    
    async def _process_message(
        self,
        topic: str,
        message: Dict[str, Any],
        config: Dict[str, Any]
    ):
        """
        Process message from queue and create learning event.
        
        Args:
            topic: Topic name
            message: Raw message from queue
            config: Topic configuration
        """
        try:
            # Import models here to avoid circular dependency
            from .models import (
                LearningEvent, LearningEventType,
                DomainType, APIType, Jurisdiction
            )
            
            # Determine event type and domain from topic
            api = APIType(config["api"].lower())
            priority = config["priority"]
            
            # Parse message based on structure
            if "prediction" in topic:
                event_type = LearningEventType.OUTCOME
                domain = DomainType.TASK_BASED
                
                event = LearningEvent(
                    event_type=event_type,
                    domain=domain,
                    api=api,
                    prediction_id=message.get("prediction_id"),
                    inputs=message.get("inputs", {}),
                    predicted=message.get("predicted"),
                    actual=message.get("actual"),
                    metadata=message.get("metadata", {}),
                    jurisdiction=Jurisdiction(
                        message.get("jurisdiction", "sandbox")
                    )
                )
            
            elif "interaction" in topic:
                event_type = LearningEventType.FEEDBACK
                domain = DomainType.USER_INTERACTION
                
                event = LearningEvent(
                    event_type=event_type,
                    domain=domain,
                    api=api,
                    inputs=message.get("query", {}),
                    predicted=message.get("response", {}),
                    actual=message.get("feedback", {}),
                    metadata=message.get("metadata", {}),
                    jurisdiction=Jurisdiction(
                        message.get("jurisdiction", "sandbox")
                    )
                )
            
            elif "security" in topic:
                event_type = LearningEventType.SECURITY
                domain = DomainType.SECURITY
                
                event = LearningEvent(
                    event_type=event_type,
                    domain=domain,
                    api=api,
                    inputs=message.get("request", {}),
                    predicted=message.get("detection", {}),
                    metadata=message.get("metadata", {}),
                    jurisdiction=Jurisdiction(
                        message.get("jurisdiction", "sandbox")
                    )
                )
            
            else:
                logger.warning(f"Unknown topic pattern: {topic}")
                return
            
            # Send to orchestrator
            await self.orchestrator.process_learning_event(event, priority)
            
            logger.debug(f"Processed message from {topic}: {event.event_id}")
        
        except Exception as e:
            logger.error(f"Error processing message from {topic}: {e}")
    
    async def ingest_direct(
        self,
        api: str,
        event_type: str,
        data: Dict[str, Any],
        priority: Optional[int] = None
    ):
        """
        Direct ingestion API for engines that want to push events directly.
        
        Args:
            api: API identifier (bue, urpe, etc.)
            event_type: Event type (prediction, outcome, etc.)
            data: Event data
            priority: Optional priority override
        """
        # Import models
        from .models import (
            LearningEvent, LearningEventType,
            DomainType, APIType, Jurisdiction
        )
        
        # Determine domain from event type
        domain_map = {
            "prediction": DomainType.TASK_BASED,
            "outcome": DomainType.TASK_BASED,
            "interaction": DomainType.USER_INTERACTION,
            "security": DomainType.SECURITY,
            "knowledge": DomainType.INTERNET,
            "synthesis": DomainType.CROSS_DOMAIN
        }
        
        domain = domain_map.get(event_type, DomainType.TASK_BASED)
        
        # Create event
        event = LearningEvent(
            event_type=LearningEventType(event_type),
            domain=domain,
            api=APIType(api.lower()),
            inputs=data.get("inputs", {}),
            predicted=data.get("predicted"),
            actual=data.get("actual"),
            learning_signal=data.get("learning_signal"),
            metadata=data.get("metadata", {}),
            jurisdiction=Jurisdiction(data.get("jurisdiction", "sandbox"))
        )
        
        # Process with default or custom priority
        if priority is None:
            priority = 5  # Default
        
        await self.orchestrator.process_learning_event(event, priority)
        
        logger.info(f"Direct ingestion: {api} {event_type} event {event.event_id}")


# ============================================================================
# ENGINE-SPECIFIC ADAPTERS
# ============================================================================

class BUEAdapter:
    """Adapter for BUE prediction/outcome events"""
    
    @staticmethod
    def prediction_to_event(prediction: Dict) -> Dict:
        """Convert BUE prediction to learning event format"""
        return {
            "inputs": {
                "company": prediction.get("company"),
                "industry": prediction.get("industry"),
                "features": prediction.get("features", {})
            },
            "predicted": {
                "risk_score": prediction.get("risk_score"),
                "default_probability": prediction.get("default_probability"),
                "confidence": prediction.get("confidence")
            },
            "metadata": {
                "model_version": prediction.get("model_version"),
                "timestamp": prediction.get("timestamp")
            }
        }
    
    @staticmethod
    def outcome_to_event(outcome: Dict) -> Dict:
        """Convert BUE outcome to learning event format"""
        return {
            "actual": {
                "default": outcome.get("default", False),
                "loss_amount": outcome.get("loss_amount", 0.0)
            },
            "metadata": {
                "outcome_date": outcome.get("outcome_date"),
                "days_since_prediction": outcome.get("days_since_prediction")
            }
        }


class URPEAdapter:
    """Adapter for URPE scenario analysis events"""
    
    @staticmethod
    def scenario_to_event(scenario: Dict) -> Dict:
        """Convert URPE scenario to learning event format"""
        return {
            "inputs": {
                "scenario_type": scenario.get("scenario_type"),
                "context": scenario.get("context", {}),
                "constraints": scenario.get("constraints", {})
            },
            "predicted": {
                "risk_level": scenario.get("risk_level"),
                "probability": scenario.get("probability"),
                "recommended_action": scenario.get("recommended_action")
            },
            "metadata": {
                "simulation_id": scenario.get("simulation_id"),
                "jurisdiction": scenario.get("jurisdiction")
            }
        }


class UIEAdapter:
    """Adapter for UIE interaction events"""
    
    @staticmethod
    def interaction_to_event(interaction: Dict) -> Dict:
        """Convert UIE interaction to learning event format"""
        return {
            "inputs": {
                "query": interaction.get("query"),
                "user_context": interaction.get("user_context", {})
            },
            "predicted": {
                "response": interaction.get("response"),
                "model_used": interaction.get("model_used"),
                "confidence": interaction.get("confidence")
            },
            "actual": {
                "user_satisfied": interaction.get("user_satisfied"),
                "feedback": interaction.get("feedback")
            },
            "metadata": {
                "response_time_ms": interaction.get("response_time_ms"),
                "tokens_used": interaction.get("tokens_used")
            }
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    async def test():
        # Mock orchestrator
        class MockOrchestrator:
            async def process_learning_event(self, event, priority):
                print(f"Received event: {event.event_type} from {event.api} (priority={priority})")
        
        orchestrator = MockOrchestrator()
        ingestion = ILEIngestionService(orchestrator)
        
        # Test BUE adapter
        print("--- Testing BUE Adapter ---")
        bue_prediction = {
            "company": "TechCorp",
            "industry": "software",
            "risk_score": 0.25,
            "default_probability": 0.02,
            "confidence": 0.85,
            "model_version": "v1.2.3"
        }
        
        event_data = BUEAdapter.prediction_to_event(bue_prediction)
        print(f"BUE Event: {event_data}")
        
        # Test direct ingestion
        print("\n--- Testing Direct Ingestion ---")
        await ingestion.ingest_direct(
            api="bue",
            event_type="outcome",
            data={
                "inputs": {"company": "TestCorp"},
                "predicted": {"risk_score": 0.3},
                "actual": {"default": False},
                "learning_signal": 0.7
            },
            priority=8
        )
        
        # Test UIE adapter
        print("\n--- Testing UIE Adapter ---")
        uie_interaction = {
            "query": "What's the weather today?",
            "response": "It's sunny and 75°F",
            "model_used": "claude-3-opus",
            "user_satisfied": True,
            "feedback": "Great response!",
            "response_time_ms": 523,
            "tokens_used": 150
        }
        
        event_data = UIEAdapter.interaction_to_event(uie_interaction)
        print(f"UIE Event: {event_data}")
        
        print("\n✅ Ingestion Service test completed!")
    
    asyncio.run(test())
