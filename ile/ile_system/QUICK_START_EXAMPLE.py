"""
ILE Quick Start Example

Demonstrates complete ILE system setup and usage with all 7 domains.
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Complete ILE system demonstration"""
    
    print("=" * 70)
    print("ILE 7-Domain System - Quick Start Example")
    print("=" * 70)
    print()
    
    # ========================================================================
    # STEP 1: Initialize Databases
    # ========================================================================
    print("📦 Step 1: Initializing databases...")
    
    from ile_system.database import init_database, db_manager
    
    await init_database(
        postgres_url="postgresql+asyncpg://ile_user:ile_pass@localhost/ile_database",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="ile_pass",
        redis_url="redis://localhost:6379/0"
    )
    
    print("✅ Databases initialized")
    print()
    
    # ========================================================================
    # STEP 2: Setup Complete ILE System
    # ========================================================================
    print("🚀 Step 2: Setting up ILE with all 7 domains...")
    
    from ile_system import setup_complete_ile_system
    from ile_system.knowledge_graph import get_knowledge_graph
    from ile_system.constitutional_validator import ConstitutionalValidator
    
    validator = ConstitutionalValidator()
    kg = get_knowledge_graph()
    
    orchestrator, domains = await setup_complete_ile_system(
        db_manager=db_manager,
        knowledge_graph=kg,
        constitutional_validator=validator
    )
    
    print("✅ All 7 domains active:")
    print("   1. Task-Based Learning")
    print("   2. Internet Learning")
    print("   3. User Interaction Learning")
    print("   4. Cross-Domain Synthesis")
    print("   5. Federated Learning")
    print("   6. Multi-LLM Coordination")
    print("   7. Function Security Learning")
    print("   + Domain Cortex (Meta-Learning)")
    print()
    
    # ========================================================================
    # STEP 3: Process Learning Events
    # ========================================================================
    print("📊 Step 3: Processing learning events...")
    print()
    
    from ile_system.models import (
        LearningEvent, LearningEventType,
        DomainType, APIType, Jurisdiction
    )
    
    # Example 1: BUE Prediction (Domain 1: Task-Based Learning)
    print("Example 1: BUE Prediction")
    print("-" * 40)
    
    bue_prediction = LearningEvent(
        event_type=LearningEventType.OUTCOME,
        domain=DomainType.TASK_BASED,
        api=APIType.BUE,
        prediction_id="pred_001",
        inputs={
            "company": "TechCorp",
            "industry": "software",
            "annual_revenue": 50000000,
            "employee_count": 250
        },
        predicted={
            "risk_score": 0.25,
            "default_probability": 0.02,
            "confidence": 0.85
        },
        metadata={
            "model_version": "v1.2.3",
            "timestamp": datetime.utcnow().isoformat()
        },
        jurisdiction=Jurisdiction.SANDBOX
    )
    
    result = await orchestrator.process_learning_event(bue_prediction, priority=7)
    
    if result["status"] == "queued":
        print(f"✅ Event queued: {result['task_id']}")
        print(f"   Decision: {result['validation'].decision}")
        print(f"   Benefit: {result['validation'].benefit_score:.1f}")
        print(f"   Harm: {result['validation'].harm_score:.1f}")
        print(f"   Net Benefit: {result['validation'].net_benefit:.1f}")
    
    print()
    
    # Example 2: BUE Outcome (Domain 1: Task-Based Learning)
    print("Example 2: BUE Outcome")
    print("-" * 40)
    
    bue_outcome = LearningEvent(
        event_type=LearningEventType.OUTCOME,
        domain=DomainType.TASK_BASED,
        api=APIType.BUE,
        prediction_id="pred_001",
        inputs={
            "company": "TechCorp",
            "industry": "software"
        },
        predicted={
            "risk_score": 0.25,
            "default_probability": 0.02
        },
        actual={
            "default": False,  # Good! Prediction was accurate
            "loss_amount": 0.0
        },
        learning_signal=0.85,  # Positive signal = good prediction
        metadata={
            "outcome_date": datetime.utcnow().isoformat(),
            "days_since_prediction": 30
        }
    )
    
    result = await orchestrator.process_learning_event(bue_outcome, priority=8)
    print(f"✅ Outcome processed: {result['status']}")
    print()
    
    # Example 3: UIE User Interaction (Domain 3: User Interaction)
    print("Example 3: UIE User Interaction")
    print("-" * 40)
    
    uie_interaction = LearningEvent(
        event_type=LearningEventType.FEEDBACK,
        domain=DomainType.USER_INTERACTION,
        api=APIType.UIE,
        inputs={
            "query": "Explain quantum computing in simple terms",
            "user_context": {
                "expertise_level": "beginner",
                "preferred_style": "conversational"
            }
        },
        predicted={
            "response": "Quantum computing uses quantum bits...",
            "model_used": "claude-3-opus",
            "confidence": 0.92
        },
        actual={
            "user_satisfied": True,
            "feedback": "Very clear and helpful!",
            "rating": 5
        },
        metadata={
            "response_time_ms": 523,
            "tokens_used": 150
        }
    )
    
    result = await orchestrator.process_learning_event(uie_interaction, priority=5)
    print(f"✅ Interaction processed: {result['status']}")
    print()
    
    # Example 4: Security Event (Domain 7: Function Security)
    print("Example 4: Security Event")
    print("-" * 40)
    
    from ile_system.models import SecurityEvent
    
    security_event = LearningEvent(
        event_type=LearningEventType.SECURITY,
        domain=DomainType.SECURITY,
        api=APIType.BUE,
        inputs={
            "event_type": "suspicious_activity",
            "severity": "medium",
            "source_ip": "203.0.113.42",
            "user_id": "user_123",
            "request_pattern": {
                "recent_requests": 50,
                "error_rate": 0.3,
                "unusual_params": ["admin", "delete", "all"]
            }
        },
        predicted={
            "threat_level": "medium",
            "should_block": False,
            "confidence": 0.75
        }
    )
    
    result = await orchestrator.process_learning_event(security_event, priority=10)
    print(f"✅ Security event processed: {result['status']}")
    print()
    
    # ========================================================================
    # STEP 4: Wait for Processing
    # ========================================================================
    print("⏳ Step 4: Processing events...")
    await asyncio.sleep(3)
    print("✅ Events processed")
    print()
    
    # ========================================================================
    # STEP 5: Get System Metrics
    # ========================================================================
    print("📈 Step 5: System metrics")
    print("-" * 40)
    
    metrics = await orchestrator.get_metrics()
    
    print(f"Total events: {metrics.total_events}")
    print(f"Processed: {metrics.processed_events}")
    print(f"Rejected: {metrics.rejected_events}")
    print(f"Approval rate: {metrics.approval_rate:.1%}")
    print(f"Avg benefit score: {metrics.avg_benefit_score:.1f}")
    print(f"Avg harm score: {metrics.avg_harm_score:.1f}")
    print()
    
    # ========================================================================
    # STEP 6: Domain-Specific Examples
    # ========================================================================
    print("🎯 Step 6: Domain-specific operations")
    print("-" * 40)
    print()
    
    # Domain 1: Get RL policy recommendations
    print("Domain 1 - Best Action Recommendation:")
    best_action = await domains.rl_learner.get_best_action(
        api="bue",
        inputs={"industry": "software", "company_size": "medium"},
        candidate_actions=["low_risk", "medium_risk", "high_risk"]
    )
    print(f"   Recommended action: {best_action}")
    print()
    
    # Domain 6: Get LLM routing weights
    print("Domain 6 - Multi-LLM Routing Weights:")
    weights = await domains.ensemble_coordinator.get_routing_weights()
    for model, weight in weights.items():
        print(f"   {model}: {weight:.1%}")
    print()
    
    # Domain Cortex: Generate performance report
    print("Domain Cortex - Performance Analysis:")
    performance = await domains.meta_learner.analyze_domain_performance()
    report = await domains.meta_learner.generate_report(performance)
    print(report)
    print()
    
    # ========================================================================
    # STEP 7: Cleanup
    # ========================================================================
    print("🧹 Step 7: Cleanup")
    print("-" * 40)
    
    from ile_system import stop_orchestrator, close_database
    
    await stop_orchestrator()
    await close_database()
    
    print("✅ System shutdown complete")
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 70)
    print("✨ ILE Quick Start Complete!")
    print("=" * 70)
    print()
    print("You have successfully:")
    print("  ✅ Initialized all databases")
    print("  ✅ Started all 7 learning domains")
    print("  ✅ Processed learning events")
    print("  ✅ Validated through constitutional governance")
    print("  ✅ Generated system metrics")
    print("  ✅ Demonstrated domain-specific operations")
    print()
    print("Next steps:")
    print("  1. Review README_COMPLETE.md for full documentation")
    print("  2. Check DEPLOYMENT_GUIDE.md for production setup")
    print("  3. Integrate with your Aetherion engines")
    print("  4. Start learning! 🚀")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
