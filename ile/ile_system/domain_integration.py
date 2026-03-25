"""
ILE Orchestrator Domain Integration

Integrates all 7 learning domains with the core orchestrator.
This file extends the orchestrator stub methods with actual domain implementations.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ============================================================================
# DOMAIN INTEGRATION CLASS
# ============================================================================

class DomainIntegration:
    """
    Integrates all 7 learning domains with the ILE orchestrator.
    
    Creates instances of domain components and wires them to orchestrator methods.
    """
    
    def __init__(
        self,
        db_manager,
        knowledge_graph,
        constitutional_validator,
        rl_engine,
        model_registry,
        anomaly_core,
        metrics_module
    ):
        """
        Initialize domain integration.
        
        Args:
            db_manager: Database manager
            knowledge_graph: Knowledge graph connector
            constitutional_validator: Constitutional validator
            rl_engine: RL engine
            model_registry: Model registry
            anomaly_core: Anomaly detection core
            metrics_module: Metrics computation module
        """
        self.db = db_manager
        self.kg = knowledge_graph
        self.validator = constitutional_validator
        self.rl = rl_engine
        self.registry = model_registry
        self.anomaly = anomaly_core
        self.metrics = metrics_module
        
        # Initialize all domains
        self._init_domain1()
        self._init_domain2()
        self._init_domain3()
        self._init_domain4()
        self._init_domain5()
        self._init_domain6()
        self._init_domain7()
        self._init_domain_cortex()
        
        logger.info("All 7 domains integrated successfully")
    
    def _init_domain1(self):
        """Initialize Domain 1: Task-Based Learning"""
        from .domains.domain1_task_based import (
            TaskOutcomeTracker,
            ReinforcementLearner,
            ModelUpdateCoordinator,
            BUELearningAdapter
        )
        
        self.task_tracker = TaskOutcomeTracker(self.db)
        self.rl_learner = ReinforcementLearner(self.rl, self.metrics)
        self.model_coordinator = ModelUpdateCoordinator(self.registry, self.validator)
        self.bue_adapter = BUELearningAdapter(self.task_tracker)
        
        logger.info("Domain 1 (Task-Based Learning) initialized")
    
    def _init_domain2(self):
        """Initialize Domain 2: Internet Learning"""
        from .domains.domain2_internet_learning import (
            WebCrawler,
            InformationExtractor,
            CredibilityScorer,
            KnowledgeIntegrator
        )
        
        self.web_crawler = WebCrawler(self.db)
        self.info_extractor = InformationExtractor()
        self.credibility_scorer = CredibilityScorer()
        self.knowledge_integrator = KnowledgeIntegrator(self.kg)
        
        logger.info("Domain 2 (Internet Learning) initialized")
    
    def _init_domain3(self):
        """Initialize Domain 3: User Interaction Learning"""
        from .domains.domain3_user_interaction import (
            UDOALearner,
            UIELearner,
            CEOALearner,
            PatternRecognizer,
            PersonalizationEngine
        )
        
        self.udoa_learner = UDOALearner(self.db)
        self.uie_learner = UIELearner(self.db)
        self.ceoa_learner = CEOALearner(self.db)
        self.pattern_recognizer = PatternRecognizer()
        self.personalization_engine = PersonalizationEngine(self.validator)
        
        logger.info("Domain 3 (User Interaction Learning) initialized")
    
    def _init_domain4(self):
        """Initialize Domain 4: Cross-Domain Learning"""
        from .domains.domain4_cross_domain import (
            PatternExtractor,
            RelevanceMapper,
            KnowledgeTranslator
        )
        
        self.pattern_extractor = PatternExtractor(self.db, self.kg)
        self.relevance_mapper = RelevanceMapper()
        self.knowledge_translator = KnowledgeTranslator(self.validator)
        
        logger.info("Domain 4 (Cross-Domain Learning) initialized")
    
    def _init_domain5(self):
        """Initialize Domain 5: Federated Learning"""
        from .domains.domain5_federated import (
            FederatedClient,
            FederatedServer
        )
        
        self.federated_server = FederatedServer(self.validator, self.registry)
        # Clients are created dynamically on edge devices
        
        logger.info("Domain 5 (Federated Learning) initialized")
    
    def _init_domain6(self):
        """Initialize Domain 6: Multi-LLM Coordination"""
        from .domains.domain6_multi_llm import EnsembleCoordinator
        
        self.ensemble_coordinator = EnsembleCoordinator(self.rl)
        
        logger.info("Domain 6 (Multi-LLM Coordination) initialized")
    
    def _init_domain7(self):
        """Initialize Domain 7: Function Security"""
        from .domains.domain7_function_security import (
            RequestSanitizer,
            SecurityAnomalyDetector,
            SecurityLearner
        )
        
        self.request_sanitizer = RequestSanitizer()
        self.security_anomaly_detector = SecurityAnomalyDetector(self.anomaly)
        self.security_learner = SecurityLearner(self.validator, self.registry)
        
        logger.info("Domain 7 (Function Security) initialized")
    
    def _init_domain_cortex(self):
        """Initialize Domain Cortex: Meta-Learning"""
        from .domains.domain_cortex import MetaLearner
        
        self.meta_learner = MetaLearner(self.db)
        
        logger.info("Domain Cortex (Meta-Learning) initialized")
    
    # ========================================================================
    # DOMAIN PROCESSORS (Called by Orchestrator)
    # ========================================================================
    
    async def process_task_based_learning(self, event: "LearningEvent") -> Dict:
        """Domain 1: Process task-based learning"""
        result = {"domain": "task_based", "processed": False}
        
        try:
            # Store prediction or outcome
            if event.predicted and not event.actual:
                await self.task_tracker.record_prediction(event)
                result["action"] = "prediction_recorded"
                result["processed"] = True
            
            elif event.actual:
                # Get recent outcomes and update RL
                outcomes = await self.task_tracker.get_unprocessed_outcomes(
                    api=event.api.value,
                    limit=100
                )
                
                if outcomes:
                    # Convert to events
                    from .models import LearningEvent, LearningEventType, DomainType
                    events = [
                        LearningEvent(
                            event_type=LearningEventType.OUTCOME,
                            domain=DomainType.TASK_BASED,
                            api=event.api,
                            inputs=o["inputs"],
                            predicted=o["predicted"],
                            actual=o["actual"],
                            learning_signal=o["learning_signal"]
                        )
                        for o in outcomes
                    ]
                    
                    # Compute metrics
                    metrics = await self.rl_learner.compute_metrics(events)
                    
                    # Update RL policies
                    await self.rl_learner.update_policy(events)
                    
                    # Propose model updates
                    proposals = await self.model_coordinator.propose_updates(metrics)
                    
                    # Apply approved updates
                    if proposals:
                        update_result = await self.model_coordinator.apply_approved_updates(proposals)
                        result["updates"] = update_result
                    
                    # Mark as processed
                    await self.task_tracker.mark_processed([o["prediction_id"] for o in outcomes])
                    
                    result["action"] = "rl_updated"
                    result["metrics"] = metrics.dict()
                    result["processed"] = True
            
            logger.info(f"Task-based learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in task-based learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_internet_learning(self, event: "LearningEvent") -> Dict:
        """Domain 2: Process internet learning"""
        result = {"domain": "internet", "processed": False}
        
        try:
            # Trigger web crawl
            urls = event.inputs.get("urls", [])
            topic = event.inputs.get("topic", "general")
            
            if urls:
                # Crawl websites
                documents = await self.web_crawler.crawl(urls, topic)
                
                # Extract knowledge
                knowledge_items = await self.info_extractor.extract_knowledge(documents)
                
                # Score credibility
                for item in knowledge_items:
                    item.credibility_score = self.credibility_scorer.score_source(
                        item.source,
                        item.source_type
                    )
                
                # Integrate into knowledge graph
                integration_result = await self.knowledge_integrator.integrate(knowledge_items)
                
                result["documents_crawled"] = len(documents)
                result["knowledge_extracted"] = len(knowledge_items)
                result["integration"] = integration_result
                result["processed"] = True
            
            logger.info(f"Internet learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in internet learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_user_interaction_learning(self, event: "LearningEvent") -> Dict:
        """Domain 3: Process user interaction learning"""
        result = {"domain": "user_interaction", "processed": False}
        
        try:
            # Route to appropriate learner
            if event.api.value == "udoa":
                # Process UDOA interaction (placeholder)
                result["learner"] = "udoa"
            elif event.api.value == "uie":
                await self.ensemble_coordinator.track_performance(event)
                result["learner"] = "uie"
            elif event.api.value == "ceoa":
                # Process CEOA interaction (placeholder)
                result["learner"] = "ceoa"
            
            result["processed"] = True
            
            logger.info(f"User interaction learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in user interaction learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_cross_domain_synthesis(self, event: "LearningEvent") -> Dict:
        """Domain 4: Process cross-domain synthesis"""
        result = {"domain": "cross_domain", "processed": False}
        
        try:
            # Extract patterns across domains
            patterns = await self.pattern_extractor.extract_patterns()
            
            # Map relevance
            relevance_map = self.relevance_mapper.map_relevance(patterns)
            
            # Translate to updates
            proposals = await self.knowledge_translator.translate_patterns(patterns, relevance_map)
            
            result["patterns_found"] = len(patterns)
            result["proposals"] = len(proposals)
            result["processed"] = True
            
            logger.info(f"Cross-domain synthesis processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in cross-domain synthesis: {e}")
            result["error"] = str(e)
            return result
    
    async def process_federated_edge_learning(self, event: "LearningEvent") -> Dict:
        """Domain 5: Process federated learning"""
        result = {"domain": "federated_edge", "processed": False}
        
        try:
            # Receive client update
            client_update = event.inputs.get("client_update")
            
            if client_update:
                await self.federated_server.receive_update(client_update)
                result["action"] = "update_received"
            
            # Check if ready to aggregate
            if event.metadata.get("aggregate", False):
                aggregated = await self.federated_server.aggregate_updates()
                
                if aggregated:
                    await self.federated_server.propose_model_update(aggregated)
                    result["action"] = "aggregated"
                    result["aggregated"] = aggregated
            
            result["processed"] = True
            
            logger.info(f"Federated learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in federated learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_multi_llm_learning(self, event: "LearningEvent") -> Dict:
        """Domain 6: Process multi-LLM coordination"""
        result = {"domain": "multi_llm", "processed": False}
        
        try:
            # Track LLM performance
            await self.ensemble_coordinator.track_performance(event)
            
            # Get current routing weights
            weights = await self.ensemble_coordinator.get_routing_weights()
            
            result["routing_weights"] = weights
            result["processed"] = True
            
            logger.info(f"Multi-LLM learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in multi-LLM learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_security_learning(self, event: "LearningEvent") -> Dict:
        """Domain 7: Process security learning"""
        result = {"domain": "security", "processed": False}
        
        try:
            from .models import SecurityEvent
            
            # Extract features
            security_event = SecurityEvent(**event.inputs)
            features = self.request_sanitizer.extract_features(security_event)
            
            # Detect anomalies
            is_anomaly, score = await self.security_anomaly_detector.detect(
                features=features,
                tenant_id=security_event.user_id or "unknown",
                function_name=security_event.request_pattern.get("function", "unknown")
            )
            
            result["is_anomaly"] = is_anomaly
            result["anomaly_score"] = score
            result["processed"] = True
            
            # If many anomalies, propose security updates
            if is_anomaly:
                proposals = await self.security_learner.propose_security_updates([{
                    "event_id": str(event.event_id),
                    "severity": security_event.severity,
                    "score": score
                }])
                
                if proposals:
                    await self.security_learner.apply_security_updates(proposals)
                    result["security_updates"] = len(proposals)
            
            logger.info(f"Security learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in security learning: {e}")
            result["error"] = str(e)
            return result
    
    async def process_domain_cortex_learning(self, event: "LearningEvent") -> Dict:
        """Domain Cortex: Process meta-learning"""
        result = {"domain": "domain_cortex", "processed": False}
        
        try:
            # Analyze performance across all domains
            performance = await self.meta_learner.analyze_domain_performance()
            
            # Generate report
            report = await self.meta_learner.generate_report(performance)
            
            result["performance_summary"] = performance
            result["report"] = report
            result["processed"] = True
            
            logger.info(f"Domain cortex learning processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error in domain cortex learning: {e}")
            result["error"] = str(e)
            return result


# ============================================================================
# INTEGRATION FUNCTION
# ============================================================================

async def integrate_domains_with_orchestrator(orchestrator, domain_integration):
    """
    Wire domain processors to orchestrator stub methods.
    
    Args:
        orchestrator: ILEOrchestrator instance
        domain_integration: DomainIntegration instance
    """
    # Replace orchestrator stub methods with actual domain processors
    orchestrator._process_task_based_learning = domain_integration.process_task_based_learning
    orchestrator._process_internet_learning = domain_integration.process_internet_learning
    orchestrator._process_user_interaction_learning = domain_integration.process_user_interaction_learning
    orchestrator._process_cross_domain_synthesis = domain_integration.process_cross_domain_synthesis
    orchestrator._process_federated_edge_learning = domain_integration.process_federated_edge_learning
    orchestrator._process_multi_llm_learning = domain_integration.process_multi_llm_learning
    orchestrator._process_security_learning = domain_integration.process_security_learning
    orchestrator._process_domain_cortex_learning = domain_integration.process_domain_cortex_learning
    
    logger.info("✅ All 7 domains integrated with orchestrator")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

async def setup_complete_ile_system(
    db_manager,
    knowledge_graph,
    constitutional_validator
):
    """
    Setup complete ILE system with all 7 domains integrated.
    
    Args:
        db_manager: Database manager
        knowledge_graph: Knowledge graph connector
        constitutional_validator: Constitutional validator
    
    Returns:
        Tuple of (orchestrator, domain_integration)
    """
    from .orchestrator import get_orchestrator
    from .rl_engine import RLEngine
    from .model_registry import get_registry
    from .anomaly_core import AnomalyDetector
    import metrics
    
    # Initialize core components
    rl_engine = RLEngine(db_manager)
    model_registry = await get_registry(db_manager)
    anomaly_core = AnomalyDetector(db_manager)
    
    # Create domain integration
    domain_integration = DomainIntegration(
        db_manager=db_manager,
        knowledge_graph=knowledge_graph,
        constitutional_validator=constitutional_validator,
        rl_engine=rl_engine,
        model_registry=model_registry,
        anomaly_core=anomaly_core,
        metrics_module=metrics
    )
    
    # Get orchestrator
    orchestrator = await get_orchestrator()
    
    # Wire domains to orchestrator
    await integrate_domains_with_orchestrator(orchestrator, domain_integration)
    
    logger.info("🚀 Complete ILE system setup successful!")
    
    return orchestrator, domain_integration
