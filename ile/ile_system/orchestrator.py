"""
Internal Learning Engine - Core Orchestrator

Central coordinator for all learning activities across the 7 learning domains.
Manages priority queue, routes events to appropriate domains, triggers cross-domain
synthesis, and coordinates with constitutional governance.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from .models import (
    LearningEvent, LearningTask, LearningMetrics, DomainType, 
    APIType, LearningEventType, ConstitutionalDecision
)
from .database import db_manager
from .constitutional_validator import ConstitutionalValidator

logger = logging.getLogger(__name__)


# ============================================================================
# ILE ORCHESTRATOR
# ============================================================================

class ILEOrchestrator:
    """
    Central coordinator for the Internal Learning Engine.
    
    Responsibilities:
    1. Receive learning events from all APIs
    2. Route to appropriate learning domains
    3. Manage priority queue
    4. Coordinate constitutional validation
    5. Trigger cross-domain synthesis
    6. Track metrics and performance
    """
    
    def __init__(self):
        self.constitutional_validator = ConstitutionalValidator()
        
        # Priority queue (1=lowest, 10=highest)
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Metrics tracking
        self.metrics: Dict[str, int] = defaultdict(int)
        self.metrics_lock = asyncio.Lock()
        
        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.num_workers = 4  # Configurable
        self.running = False
        
        # Cross-domain synthesis tracking
        self.synthesis_triggers: Dict[str, int] = defaultdict(int)
        self.synthesis_threshold = 100  # Trigger after N events
        
        logger.info("ILE Orchestrator initialized")
    
    async def start(self):
        """Start the orchestrator and worker tasks"""
        if self.running:
            logger.warning("Orchestrator already running")
            return
        
        self.running = True
        
        # Start worker tasks
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        
        logger.info(f"ILE Orchestrator started with {self.num_workers} workers")
    
    async def stop(self):
        """Stop the orchestrator gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping ILE Orchestrator...")
        self.running = False
        
        # Wait for queue to empty
        await self.task_queue.join()
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("ILE Orchestrator stopped")
    
    async def process_learning_event(
        self,
        event: LearningEvent,
        priority: int = 5
    ) -> Dict[str, any]:
        """
        Process a learning event through the full pipeline.
        
        Args:
            event: Learning event to process
            priority: Priority level (1=lowest, 10=highest)
        
        Returns:
            Processing result including constitutional decision
        """
        try:
            # Step 1: Constitutional validation
            validation = await self.constitutional_validator.validate_learning(event)
            
            async with self.metrics_lock:
                self.metrics["total_events"] += 1
                self.metrics[f"events_{event.domain}"] += 1
                self.metrics[f"events_{event.api}"] += 1
            
            # Step 2: Check if approved
            if validation.decision == ConstitutionalDecision.REJECTED:
                logger.warning(
                    f"Learning event rejected: {validation.decision_reason}"
                )
                async with self.metrics_lock:
                    self.metrics["rejected_events"] += 1
                
                # Store rejection in database
                await self._store_rejection(event, validation)
                
                return {
                    "status": "rejected",
                    "validation": validation,
                    "reason": validation.decision_reason
                }
            
            # Step 3: Create learning task
            task = LearningTask(
                event=event,
                priority=priority
            )
            
            # Step 4: Add to priority queue (lower number = higher priority)
            await self.task_queue.put((-priority, task))
            
            async with self.metrics_lock:
                self.metrics["queued_events"] += 1
            
            logger.info(
                f"Learning event queued: {event.event_type} from {event.domain} "
                f"(priority={priority})"
            )
            
            # Step 5: Check if cross-domain synthesis needed
            await self._check_synthesis_trigger(event)
            
            return {
                "status": "queued",
                "validation": validation,
                "task_id": str(task.task_id)
            }
        
        except Exception as e:
            logger.error(f"Error processing learning event: {e}", exc_info=True)
            async with self.metrics_lock:
                self.metrics["error_events"] += 1
            raise
    
    async def _worker(self, worker_id: int):
        """
        Worker task that processes learning events from the queue.
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get task from queue (with timeout to allow shutdown)
                try:
                    priority, task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process task
                try:
                    task.status = "processing"
                    task.started_at = datetime.utcnow()
                    task.attempts += 1
                    
                    logger.info(
                        f"Worker {worker_id} processing task {task.task_id} "
                        f"from domain {task.event.domain}"
                    )
                    
                    # Route to appropriate domain
                    result = await self._route_to_domain(task)
                    
                    # Mark as completed
                    task.status = "completed"
                    task.completed_at = datetime.utcnow()
                    task.result = result
                    
                    async with self.metrics_lock:
                        self.metrics["processed_events"] += 1
                        self.metrics[f"processed_{task.event.domain}"] += 1
                    
                    logger.info(
                        f"Worker {worker_id} completed task {task.task_id}"
                    )
                
                except Exception as e:
                    logger.error(
                        f"Worker {worker_id} error processing task {task.task_id}: {e}",
                        exc_info=True
                    )
                    
                    task.error = str(e)
                    
                    # Retry if under max attempts
                    if task.attempts < task.max_attempts:
                        logger.info(
                            f"Retrying task {task.task_id} "
                            f"(attempt {task.attempts + 1}/{task.max_attempts})"
                        )
                        await self.task_queue.put((priority, task))
                    else:
                        task.status = "failed"
                        task.completed_at = datetime.utcnow()
                        
                        async with self.metrics_lock:
                            self.metrics["failed_events"] += 1
                
                finally:
                    self.task_queue.task_done()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}", exc_info=True)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _route_to_domain(self, task: LearningTask) -> Dict[str, any]:
        """
        Route learning task to appropriate domain for processing.
        
        This is a router - actual domain implementations will be in separate modules.
        """
        event = task.event
        domain = event.domain
        
        # Domain routing logic
        if domain == DomainType.TASK_BASED:
            result = await self._process_task_based_learning(event)
        
        elif domain == DomainType.INTERNET:
            result = await self._process_internet_learning(event)
        
        elif domain == DomainType.USER_INTERACTION:
            result = await self._process_user_interaction_learning(event)
        
        elif domain == DomainType.CROSS_DOMAIN:
            result = await self._process_cross_domain_synthesis(event)
        
        elif domain == DomainType.FEDERATED_EDGE:
            result = await self._process_federated_edge_learning(event)
        
        elif domain == DomainType.MULTI_LLM:
            result = await self._process_multi_llm_learning(event)
        
        elif domain == DomainType.SECURITY:
            result = await self._process_security_learning(event)
        
        elif domain == DomainType.DOMAIN_CORTEX:
            result = await self._process_domain_cortex_learning(event)
        
        else:
            raise ValueError(f"Unknown domain: {domain}")
        
        return result
    
    # ========================================================================
    # DOMAIN-SPECIFIC PROCESSING (Stubs - implemented in domain modules)
    # ========================================================================
    
    async def _process_task_based_learning(self, event: LearningEvent) -> Dict:
        """Domain 1: Task-Based Learning"""
        logger.info(f"Processing task-based learning for {event.api}")
        
        # This will be implemented in domains/domain1_task_based/
        # For now, return stub response
        return {
            "domain": "task_based",
            "status": "stub_implementation",
            "note": "Full implementation in domains/domain1_task_based/"
        }
    
    async def _process_internet_learning(self, event: LearningEvent) -> Dict:
        """Domain 2: Internet Learning"""
        logger.info("Processing internet learning")
        return {"domain": "internet", "status": "stub_implementation"}
    
    async def _process_user_interaction_learning(self, event: LearningEvent) -> Dict:
        """Domain 3: User Interaction Learning"""
        logger.info("Processing user interaction learning")
        return {"domain": "user_interaction", "status": "stub_implementation"}
    
    async def _process_cross_domain_synthesis(self, event: LearningEvent) -> Dict:
        """Domain 4: Cross-Domain Synthesis"""
        logger.info("Processing cross-domain synthesis")
        return {"domain": "cross_domain", "status": "stub_implementation"}
    
    async def _process_federated_edge_learning(self, event: LearningEvent) -> Dict:
        """Domain 5: Federated Edge Learning"""
        logger.info("Processing federated edge learning")
        return {"domain": "federated_edge", "status": "stub_implementation"}
    
    async def _process_multi_llm_learning(self, event: LearningEvent) -> Dict:
        """Domain 6: Multi-LLM Coordination"""
        logger.info("Processing multi-LLM learning")
        return {"domain": "multi_llm", "status": "stub_implementation"}
    
    async def _process_security_learning(self, event: LearningEvent) -> Dict:
        """Domain 7: Security Learning"""
        logger.info("Processing security learning")
        return {"domain": "security", "status": "stub_implementation"}
    
    async def _process_domain_cortex_learning(self, event: LearningEvent) -> Dict:
        """Domain Cortex: Meta-Learning"""
        logger.info("Processing domain cortex learning")
        return {"domain": "domain_cortex", "status": "stub_implementation"}
    
    # ========================================================================
    # CROSS-DOMAIN SYNTHESIS MANAGEMENT
    # ========================================================================
    
    async def _check_synthesis_trigger(self, event: LearningEvent):
        """
        Check if cross-domain synthesis should be triggered.
        
        Synthesis is triggered when:
        1. Accumulated enough events across domains
        2. Significant patterns detected
        3. Explicit synthesis request
        """
        # Track events by domain
        key = f"{event.domain}_{event.api}"
        self.synthesis_triggers[key] += 1
        
        # Check if threshold reached
        total_events = sum(self.synthesis_triggers.values())
        
        if total_events >= self.synthesis_threshold:
            logger.info(
                f"Cross-domain synthesis threshold reached ({total_events} events)"
            )
            
            # Create synthesis event
            synthesis_event = LearningEvent(
                event_type=LearningEventType.SYNTHESIS,
                domain=DomainType.CROSS_DOMAIN,
                api=event.api,  # Originating API
                inputs={"trigger_events": dict(self.synthesis_triggers)},
                metadata={"automatic_trigger": True}
            )
            
            # Process with high priority
            await self.process_learning_event(synthesis_event, priority=8)
            
            # Reset counters
            self.synthesis_triggers.clear()
    
    async def _store_rejection(self, event: LearningEvent, validation):
        """Store rejected learning event for audit trail"""
        if not db_manager:
            return
        
        try:
            async with db_manager.postgres_session() as session:
                from .database import LearningEventTable
                from sqlalchemy import insert
                
                await session.execute(
                    insert(LearningEventTable).values(
                        event_id=str(event.event_id),
                        event_type=event.event_type.value,
                        domain=event.domain.value,
                        api=event.api.value,
                        timestamp=event.timestamp,
                        prediction_id=event.prediction_id,
                        inputs=event.inputs,
                        predicted=event.predicted,
                        actual=event.actual,
                        learning_signal=event.learning_signal,
                        metadata={
                            **event.metadata,
                            "rejected": True,
                            "rejection_reason": validation.decision_reason
                        },
                        jurisdiction=event.jurisdiction.value
                    )
                )
        except Exception as e:
            logger.error(f"Error storing rejection: {e}")
    
    # ========================================================================
    # METRICS AND MONITORING
    # ========================================================================
    
    async def get_metrics(self) -> LearningMetrics:
        """
        Get current learning metrics.
        """
        async with self.metrics_lock:
            total_events = self.metrics.get("total_events", 0)
            processed = self.metrics.get("processed_events", 0)
            rejected = self.metrics.get("rejected_events", 0)
            
            approval_rate = (
                (processed / total_events) if total_events > 0 else 1.0
            )
            
            return LearningMetrics(
                timeframe_minutes=60,  # Last hour
                total_events=total_events,
                processed_events=processed,
                rejected_events=rejected,
                approval_rate=approval_rate,
                avg_benefit_score=0.0,  # Computed from database
                avg_harm_score=0.0,  # Computed from database
                avg_processing_time_ms=0.0,  # Computed from task timing
                knowledge_items_added=0,  # From knowledge graph
                patterns_discovered=0  # From pattern detector
            )
    
    async def get_queue_status(self) -> Dict[str, any]:
        """Get current queue status"""
        return {
            "queue_size": self.task_queue.qsize(),
            "workers": len(self.workers),
            "running": self.running,
            "metrics": await self.get_metrics()
        }
    
    async def reset_metrics(self):
        """Reset metrics counters"""
        async with self.metrics_lock:
            self.metrics.clear()
        logger.info("Metrics reset")


# ============================================================================
# GLOBAL ORCHESTRATOR INSTANCE
# ============================================================================

_orchestrator: Optional[ILEOrchestrator] = None


async def get_orchestrator() -> ILEOrchestrator:
    """Get global orchestrator instance (singleton pattern)"""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = ILEOrchestrator()
        await _orchestrator.start()
    
    return _orchestrator


async def stop_orchestrator():
    """Stop global orchestrator"""
    global _orchestrator
    
    if _orchestrator:
        await _orchestrator.stop()
        _orchestrator = None


# ============================================================================
# MAIN - For standalone testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        """Test orchestrator functionality"""
        orchestrator = await get_orchestrator()
        
        # Create test learning event
        event = LearningEvent(
            event_type=LearningEventType.OUTCOME,
            domain=DomainType.TASK_BASED,
            api=APIType.BUE,
            prediction_id="test_001",
            inputs={"company": "Test Corp"},
            predicted={"risk_score": 0.25},
            actual={"default": False},
            learning_signal=0.75
        )
        
        # Process event
        result = await orchestrator.process_learning_event(event, priority=7)
        
        print(f"\nProcessing result: {result}")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Get metrics
        metrics = await orchestrator.get_metrics()
        print(f"\nMetrics: {metrics}")
        
        # Get queue status
        status = await orchestrator.get_queue_status()
        print(f"\nQueue status: {status}")
        
        # Stop orchestrator
        await stop_orchestrator()
        
        print("\n✅ Orchestrator test completed successfully!")
    
    asyncio.run(test())
