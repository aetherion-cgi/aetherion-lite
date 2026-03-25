"""
Aetherion Internal Learning Engine (ILE)

Complete 7-domain learning system with constitutional governance.

Author: Aetherion Development Team
Date: November 15, 2025
Version: 1.0.0
"""

"""ILE package initializer.

Keep this file lightweight so internal-only local MVP boot does not eagerly import
DB/graph dependencies such as asyncpg or neo4j.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]

# Core infrastructure exports
'''from .models import (
    DomainType,
    APIType,
    LearningEventType,
    ConstitutionalDecision,
    Jurisdiction,
    LearningEvent,
    TaskOutcome,
    KnowledgeItem,
    ConstitutionalValidation,
    AuditLogEntry,
    LearningMetrics,
    ModelPerformance,
    CrossDomainPattern,
    UserInteraction,
    SecurityEvent,
)

from .database import (
    DatabaseManager,
    init_database,
    close_database,
    db_manager,
)

from .orchestrator import (
    ILEOrchestrator,
    get_orchestrator,
    stop_orchestrator,
)

from .constitutional_validator import ConstitutionalValidator

from .knowledge_graph import (
    KnowledgeGraphConnector,
    get_knowledge_graph,
)

# Core helpers
from .rl_engine import RLEngine, MultiArmedBandit
from .model_registry import ModelRegistry, get_registry
from .anomaly_core import AnomalyDetector, TimeSeriesAnomalyDetector
from .ingestion import ILEIngestionService, BUEAdapter, URPEAdapter, UIEAdapter
import metrics

# Domain integration
from .domain_integration import (
    DomainIntegration,
    integrate_domains_with_orchestrator,
    setup_complete_ile_system,
)

# Domain exports
from .domains.domain1_task_based import (
    TaskOutcomeTracker,
    ReinforcementLearner,
    ModelUpdateCoordinator,
    BUELearningAdapter,
)

from .domains.domain2_internet_learning import (
    WebCrawler,
    InformationExtractor,
    CredibilityScorer,
    KnowledgeIntegrator,
)

from .domains.domain3_user_interaction import (
    UDOALearner,
    UIELearner,
    CEOALearner,
    PatternRecognizer,
    PersonalizationEngine,
)

from .domains.domain4_cross_domain import (
    PatternExtractor,
    RelevanceMapper,
    KnowledgeTranslator,
)

from .domains.domain5_federated import (
    FederatedClient,
    FederatedServer,
)

from .domains.domain6_multi_llm import EnsembleCoordinator

from .domains.domain7_function_security import (
    RequestSanitizer,
    SecurityAnomalyDetector,
    SecurityLearner,
)

from .domains.domain_cortex import MetaLearner

__all__ = [
    # Version
    "__version__",
    "__author__",
    
    # Enums
    "DomainType",
    "APIType",
    "LearningEventType",
    "ConstitutionalDecision",
    "Jurisdiction",
    
    # Core models
    "LearningEvent",
    "TaskOutcome",
    "KnowledgeItem",
    "ConstitutionalValidation",
    "AuditLogEntry",
    "LearningMetrics",
    "ModelPerformance",
    "CrossDomainPattern",
    "UserInteraction",
    "SecurityEvent",
    
    # Core infrastructure
    "DatabaseManager",
    "init_database",
    "close_database",
    "db_manager",
    "ILEOrchestrator",
    "get_orchestrator",
    "stop_orchestrator",
    "ConstitutionalValidator",
    "KnowledgeGraphConnector",
    "get_knowledge_graph",
    
    # Core helpers
    "RLEngine",
    "MultiArmedBandit",
    "ModelRegistry",
    "get_registry",
    "AnomalyDetector",
    "TimeSeriesAnomalyDetector",
    "ILEIngestionService",
    "BUEAdapter",
    "URPEAdapter",
    "UIEAdapter",
    "metrics",
    
    # Domain integration
    "DomainIntegration",
    "integrate_domains_with_orchestrator",
    "setup_complete_ile_system",
    
    # Domain 1: Task-Based Learning
    "TaskOutcomeTracker",
    "ReinforcementLearner",
    "ModelUpdateCoordinator",
    "BUELearningAdapter",
    
    # Domain 2: Internet Learning
    "WebCrawler",
    "InformationExtractor",
    "CredibilityScorer",
    "KnowledgeIntegrator",
    
    # Domain 3: User Interaction
    "UDOALearner",
    "UIELearner",
    "CEOALearner",
    "PatternRecognizer",
    "PersonalizationEngine",
    
    # Domain 4: Cross-Domain
    "PatternExtractor",
    "RelevanceMapper",
    "KnowledgeTranslator",
    
    # Domain 5: Federated Learning
    "FederatedClient",
    "FederatedServer",
    
    # Domain 6: Multi-LLM
    "EnsembleCoordinator",
    
    # Domain 7: Security
    "RequestSanitizer",
    "SecurityAnomalyDetector",
    "SecurityLearner",
    
    # Domain Cortex: Meta-Learning
    "MetaLearner",
]'''
